# -*- coding: utf-8 -*-
"""
-------------------------------------------------
   File Name：     virtualProxy
   Description :   统一入口服务器 — 对外暴露单个端口，根据请求特征自动分流：
                   CONNECT / 绝对URL → 代理转发（虚拟代理服务器）
                   相对路径 → 反向代理到 Flask/gunicorn（Web API + Dashboard）
                   每次代理调用记录审计日志（成功/失败、代理IP、状态码、目标URL等）。
                   支持代理分流：HTTP/HTTPS 直连、SOCKS5 握手、加密协议通过 mihomo。
   date：          2026/06/16
-------------------------------------------------
"""

import os
import sys
import time
import asyncio
import logging
import struct

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from handler.proxyHandler import ProxyHandler
from handler.configHandler import ConfigHandler
from helper.proxy import SCHEMES_ENCRYPTED
from proxyServer.auditLog import AuditLogger

log = logging.getLogger("virtual_proxy")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)

MAX_RETRIES = int(os.getenv("VIRTUAL_PROXY_RETRIES", "3"))
CONNECT_TIMEOUT = 8
READ_TIMEOUT = 15
PIPE_BUF = 65536

AUDIT_FILE = os.getenv("VIRTUAL_PROXY_AUDIT_FILE", "logs/virtual_proxy_audit.log")
AUDIT_SIZE_KB = int(os.getenv("VIRTUAL_PROXY_AUDIT_SIZE_KB", "1024"))
AUDIT_BACKUP_COUNT = int(os.getenv("VIRTUAL_PROXY_AUDIT_BACKUP_COUNT", "5"))


class VirtualProxyServer:
    def __init__(self, host="0.0.0.0", port=5010, flask_host="127.0.0.1", flask_port=5010):
        self.host = host
        self.port = port
        self.flask_host = flask_host
        self.flask_port = flask_port
        self.proxy_handler = ProxyHandler()
        self.audit = AuditLogger(
            file_path=AUDIT_FILE,
            max_size_kb=AUDIT_SIZE_KB,
            backup_count=AUDIT_BACKUP_COUNT,
        )
        self.conf = ConfigHandler()
        # 加密协议请求需要串行化（mihomo selector 是全局唯一）
        self._mihomo_lock = asyncio.Lock()
        self._mihomo_client = None  # 懒加载
        # 不区分 scheme 时取任意可用代理
        self._try_http_first = True

    def _get_mihomo_client(self):
        if self._mihomo_client is None:
            try:
                from handler.mihomoHandler import MihomoClient
                self._mihomo_client = MihomoClient()
            except Exception as exc:
                log.warning("mihomo client init err: %s", exc)
                return None
        return self._mihomo_client

    def _pick_proxy(self, exclude=None, scheme=None):
        """从池子里选代理；指定 scheme 时只取该类型"""
        for _ in range(5):
            proxy = self.proxy_handler.get(scheme=scheme)
            if not proxy:
                return None
            if not exclude or proxy.proxy not in exclude:
                return proxy
        return proxy if proxy else None

    def _mark_used(self, proxy_obj):
        try:
            self.proxy_handler.incrementUseCount(proxy_obj)
        except Exception:
            pass

    async def start(self):
        server = await asyncio.start_server(self._handle_client, self.host, self.port)
        addrs = ", ".join(str(s.getsockname()) for s in server.sockets)
        log.info(
            "UnifiedServer listening on %s → Flask %s:%d | audit=%s size=%dKB",
            addrs, self.flask_host, self.flask_port, AUDIT_FILE, AUDIT_SIZE_KB,
        )
        async with server:
            await server.serve_forever()

    async def _handle_client(self, reader, writer):
        addr = writer.get_extra_info("peername")
        client_str = f"{addr[0]}:{addr[1]}" if addr else "unknown"
        try:
            head = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=15)
        except (asyncio.IncompleteReadError, asyncio.TimeoutError, ConnectionError):
            writer.close()
            return
        except Exception:
            writer.close()
            return

        first_line = head.split(b"\r\n", 1)[0].decode("ascii", errors="ignore")
        parts = first_line.split()
        if len(parts) < 3:
            await self._write_response(writer, 400, b"Bad Request")
            return

        method, target = parts[0], parts[1]

        if method == "CONNECT":
            await self._handle_connect(reader, writer, target, client_str, head)
        elif target.startswith("http://") or target.startswith("https://"):
            await self._handle_http(reader, writer, method, target, client_str, head)
        else:
            await self._handle_web(reader, writer, method, target, client_str, head)

    async def _handle_connect(self, reader, writer, target, client_str, head):
        """CONNECT 方法：按 scheme 分流到 http/socks5/mihomo"""
        start = time.time()
        tried = set()
        last_proxy = ""
        last_error = ""
        for _ in range(MAX_RETRIES):
            proxy_obj = self._pick_proxy(exclude=tried)
            if not proxy_obj:
                last_error = "no proxy available"
                break
            tried.add(proxy_obj.proxy)
            last_proxy = proxy_obj.proxy

            try:
                if proxy_obj.scheme in SCHEMES_ENCRYPTED:
                    # 加密协议：经 mihomo 转发
                    success = await self._connect_via_mihomo(
                        reader, writer, proxy_obj, target, client_str,
                    )
                elif proxy_obj.scheme == "socks5":
                    # SOCKS5 代理：握手 + raw 隧道
                    success = await self._connect_via_socks5(
                        reader, writer, proxy_obj, target, client_str,
                    )
                else:
                    # HTTP/HTTPS 代理：发送 CONNECT 请求
                    success = await self._connect_via_http(
                        reader, writer, proxy_obj, target, client_str, head,
                    )
                if success:
                    duration = round(time.time() - start, 3)
                    self.audit.log(client_str, "CONNECT", target, proxy_obj.proxy,
                                   True, 200, duration)
                    return
                last_error = "upstream handshake failed"
            except asyncio.TimeoutError:
                last_error = "handshake timeout"
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                log.debug("CONNECT %s via %s err: %s", target, proxy_obj.proxy, exc)

        duration = round(time.time() - start, 3)
        self.audit.log(client_str, "CONNECT", target, last_proxy,
                       False, 502, duration, error=last_error)
        await self._write_response(writer, 502, b"Bad Gateway")

    async def _handle_http(self, reader, writer, method, target, client_str, head):
        """HTTP/HTTPS 绝对 URL 请求：按 scheme 分流"""
        start = time.time()
        tried = set()
        last_proxy = ""
        last_error = ""
        for _ in range(MAX_RETRIES):
            proxy_obj = self._pick_proxy(exclude=tried)
            if not proxy_obj:
                last_error = "no proxy available"
                break
            tried.add(proxy_obj.proxy)
            last_proxy = proxy_obj.proxy

            try:
                if proxy_obj.scheme in SCHEMES_ENCRYPTED:
                    # 加密协议：经 mihomo 转发，path 由 CONNECT 语义改为完整 URL
                    status = await self._http_via_mihomo(
                        reader, writer, proxy_obj, target, method, head, client_str,
                    )
                elif proxy_obj.scheme == "socks5":
                    status = await self._http_via_socks5(
                        reader, writer, proxy_obj, target, method, head, client_str,
                    )
                else:
                    status = await self._http_via_http(
                        reader, writer, proxy_obj, target, method, head, client_str,
                    )
                success = status > 0
                duration = round(time.time() - start, 3)
                self.audit.log(client_str, method, target, proxy_obj.proxy,
                               success, status, duration,
                               error="" if success else "no valid http response")
                if success:
                    return
                last_error = "no valid http response"
            except asyncio.TimeoutError:
                last_error = "timeout"
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                log.debug("HTTP %s via %s err: %s", target[:60], proxy_obj.proxy, exc)

        duration = round(time.time() - start, 3)
        self.audit.log(client_str, method, target, last_proxy,
                       False, 502, duration, error=last_error)
        await self._write_response(writer, 502, b"Bad Gateway")

    # ==================== HTTP 上游（原逻辑） ====================

    async def _connect_via_http(self, c_reader, c_writer, proxy_obj, target, client_str, head):
        """通过 HTTP 代理建立 CONNECT 隧道"""
        ph, pp = proxy_obj.proxy.rsplit(":", 1)
        up_r, up_w = await asyncio.wait_for(
            asyncio.open_connection(ph, int(pp)), timeout=CONNECT_TIMEOUT
        )
        try:
            up_w.write(
                f"CONNECT {target} HTTP/1.1\r\nHost: {target}\r\n\r\n".encode()
            )
            await up_w.drain()
            resp = await asyncio.wait_for(
                up_r.readuntil(b"\r\n\r\n"), timeout=READ_TIMEOUT
            )
            status_line = resp.split(b"\r\n", 1)[0]
            if b" 200 " not in status_line:
                up_w.close()
                return False
            c_writer.write(b"HTTP/1.1 200 Connection established\r\n\r\n")
            await c_writer.drain()
            log.info("CONNECT %s via %s (%s)", target, proxy_obj.proxy, client_str)
            self._mark_used(proxy_obj)
            await self._pipe(c_reader, c_writer, up_r, up_w, capture_status=False)
            return True
        finally:
            try:
                up_w.close()
            except Exception:
                pass

    async def _http_via_http(self, c_reader, c_writer, proxy_obj, target, method, head, client_str):
        """通过 HTTP 代理转发绝对 URL 请求"""
        ph, pp = proxy_obj.proxy.rsplit(":", 1)
        up_r, up_w = await asyncio.wait_for(
            asyncio.open_connection(ph, int(pp)), timeout=CONNECT_TIMEOUT
        )
        try:
            up_w.write(head)
            await up_w.drain()
            log.info("HTTP %s %s via %s (%s)", method, target[:60], proxy_obj.proxy, client_str)
            self._mark_used(proxy_obj)
            return await self._pipe(c_reader, c_writer, up_r, up_w, capture_status=True)
        finally:
            try:
                up_w.close()
            except Exception:
                pass

    # ==================== SOCKS5 上游 ====================

    async def _socks5_handshake(self, up_r, up_w, target):
        """SOCKS5 握手：协议协商 + 连接请求
        target: host:port
        """
        host, _, port_str = target.partition(":")
        port = int(port_str or "443")

        # 1. 问候：version=5, methods=[no-auth(0)]
        up_w.write(b"\x05\x01\x00")
        await up_w.drain()
        resp = await asyncio.wait_for(up_r.readexactly(2), timeout=READ_TIMEOUT)
        if resp[0] != 0x05 or resp[1] != 0x00:
            raise ConnectionError(f"socks5 method selection failed: {resp.hex()}")

        # 2. 连接请求：CMD=CONNECT(1), ATYP=DOMAINNAME(3)
        try:
            ip_bytes = bytes(int(b) for b in host.split("."))
            if len(ip_bytes) == 4:
                # IPv4
                req = b"\x05\x01\x00\x01" + ip_bytes + struct.pack(">H", port)
            else:
                raise ValueError()
        except Exception:
            # 域名
            host_bytes = host.encode("idna") if not host.isdigit() else host.encode()
            req = b"\x05\x01\x00\x03" + bytes([len(host_bytes)]) + host_bytes + struct.pack(">H", port)
        up_w.write(req)
        await up_w.drain()

        # 3. 响应
        rep = await asyncio.wait_for(up_r.readexactly(4), timeout=READ_TIMEOUT)
        if rep[0] != 0x05 or rep[1] != 0x00:
            raise ConnectionError(f"socks5 connect failed: rep={rep[1]}")
        atyp = rep[3]
        if atyp == 0x01:
            await up_r.readexactly(4 + 2)  # IPv4 + port
        elif atyp == 0x03:
            length = (await up_r.readexactly(1))[0]
            await up_r.readexactly(length + 2)
        elif atyp == 0x04:
            await up_r.readexactly(16 + 2)
        else:
            raise ConnectionError(f"socks5 unknown atyp: {atyp}")

    async def _connect_via_socks5(self, c_reader, c_writer, proxy_obj, target, client_str):
        """通过 SOCKS5 代理建立 CONNECT 隧道"""
        ph, pp = proxy_obj.proxy.rsplit(":", 1)
        up_r, up_w = await asyncio.wait_for(
            asyncio.open_connection(ph, int(pp)), timeout=CONNECT_TIMEOUT
        )
        try:
            await self._socks5_handshake(up_r, up_w, target)
            c_writer.write(b"HTTP/1.1 200 Connection established\r\n\r\n")
            await c_writer.drain()
            log.info("CONNECT(SOCKS5) %s via %s (%s)", target, proxy_obj.proxy, client_str)
            self._mark_used(proxy_obj)
            await self._pipe(c_reader, c_writer, up_r, up_w, capture_status=False)
            return True
        finally:
            try:
                up_w.close()
            except Exception:
                pass

    async def _http_via_socks5(self, c_reader, c_writer, proxy_obj, target, method, head, client_str):
        """通过 SOCKS5 代理转发绝对 URL 请求
        SOCKS5 不支持相对 URL，需要先解析出 target host:port
        """
        # target 形如 http://host:port/path
        try:
            from urllib.parse import urlparse
            parsed = urlparse(target)
            target_host = parsed.hostname or ""
            target_port = parsed.port or (443 if parsed.scheme == "https" else 80)
        except Exception:
            return 0

        ph, pp = proxy_obj.proxy.rsplit(":", 1)
        up_r, up_w = await asyncio.wait_for(
            asyncio.open_connection(ph, int(pp)), timeout=CONNECT_TIMEOUT
        )
        try:
            await self._socks5_handshake(up_r, up_w, f"{target_host}:{target_port}")
            up_w.write(head)
            await up_w.drain()
            log.info("HTTP(SOCKS5) %s %s via %s (%s)", method, target[:60], proxy_obj.proxy, client_str)
            self._mark_used(proxy_obj)
            return await self._pipe(c_reader, c_writer, up_r, up_w, capture_status=True)
        finally:
            try:
                up_w.close()
            except Exception:
                pass

    # ==================== mihomo（加密协议）上游 ====================

    def _get_node_name(self, proxy_obj):
        """从 Proxy.raw_uri 提取 Clash 用的节点 name"""
        if not proxy_obj.raw_uri:
            return None
        try:
            from handler.mihomoHandler import _uri_to_clash_entry
            entry = _uri_to_clash_entry(proxy_obj.raw_uri, proxy_obj.scheme)
            return entry.get("name") if entry else None
        except Exception:
            return None

    async def _connect_via_mihomo(self, c_reader, c_writer, proxy_obj, target, client_str):
        """加密协议：经 mihomo SOCKS5 转发 CONNECT 隧道"""
        client = self._get_mihomo_client()
        if not client:
            return False
        async with self._mihomo_lock:
            node_name = self._get_node_name(proxy_obj)
            if node_name:
                client.switch_selector(node_name)
            mihomo_host = self.conf.mihomoSocksHost
            mihomo_port = self.conf.mihomoSocksPort
            up_r, up_w = await asyncio.wait_for(
                asyncio.open_connection(mihomo_host, mihomo_port), timeout=CONNECT_TIMEOUT
            )
            try:
                await self._socks5_handshake(up_r, up_w, target)
                c_writer.write(b"HTTP/1.1 200 Connection established\r\n\r\n")
                await c_writer.drain()
                log.info("CONNECT(mihomo) %s via %s (%s)", target, proxy_obj.scheme, client_str)
                self._mark_used(proxy_obj)
                await self._pipe(c_reader, c_writer, up_r, up_w, capture_status=False)
                return True
            finally:
                try:
                    up_w.close()
                except Exception:
                    pass

    async def _http_via_mihomo(self, c_reader, c_writer, proxy_obj, target, method, head, client_str):
        """加密协议：经 mihomo SOCKS5 转发绝对 URL 请求"""
        client = self._get_mihomo_client()
        if not client:
            return 0
        try:
            from urllib.parse import urlparse
            parsed = urlparse(target)
            target_host = parsed.hostname or ""
            target_port = parsed.port or (443 if parsed.scheme == "https" else 80)
        except Exception:
            return 0

        async with self._mihomo_lock:
            node_name = self._get_node_name(proxy_obj)
            if node_name:
                client.switch_selector(node_name)
            mihomo_host = self.conf.mihomoSocksHost
            mihomo_port = self.conf.mihomoSocksPort
            up_r, up_w = await asyncio.wait_for(
                asyncio.open_connection(mihomo_host, mihomo_port), timeout=CONNECT_TIMEOUT
            )
            try:
                await self._socks5_handshake(up_r, up_w, f"{target_host}:{target_port}")
                up_w.write(head)
                await up_w.drain()
                log.info("HTTP(mihomo) %s %s via %s (%s)",
                         method, target[:60], proxy_obj.scheme, client_str)
                self._mark_used(proxy_obj)
                return await self._pipe(c_reader, c_writer, up_r, up_w, capture_status=True)
            finally:
                try:
                    up_w.close()
                except Exception:
                    pass

    # ==================== Web 反向代理 + 通用 pipe ====================

    async def _handle_web(self, reader, writer, method, target, client_str, head):
        """相对路径请求 → 反向代理到内部 Flask/gunicorn"""
        up_r, up_w = None, None
        try:
            up_r, up_w = await asyncio.wait_for(
                asyncio.open_connection(self.flask_host, self.flask_port), timeout=5
            )
            up_w.write(head)
            await up_w.drain()
            await self._pipe(reader, writer, up_r, up_w, capture_status=False)
        except Exception as exc:
            log.warning("WEB %s %s → %s:%d err: %s", method, target[:60],
                        self.flask_host, self.flask_port, exc)
            await self._write_response(writer, 502, b"Bad Gateway")
        finally:
            if up_w:
                try:
                    up_w.close()
                except Exception:
                    pass

    async def _pipe(self, c_r, c_w, u_r, u_w, capture_status=False):
        """双向字节流转发。capture_status=True 时解析首个上游响应行返回 HTTP 状态码"""
        status_holder = {"status": 0}

        async def forward(src, dst, is_upstream=False):
            first = True
            try:
                while True:
                    data = await src.read(PIPE_BUF)
                    if not data:
                        break
                    if capture_status and is_upstream and first:
                        first = False
                        status_holder["status"] = self._parse_status_from_chunk(data)
                    dst.write(data)
                    await dst.drain()
            except Exception:
                pass
            finally:
                try:
                    dst.close()
                except Exception:
                    pass

        await asyncio.gather(
            forward(c_r, u_w),
            forward(u_r, c_w, is_upstream=True),
            return_exceptions=True,
        )
        return status_holder["status"]

    @staticmethod
    def _parse_status_from_chunk(data):
        nl = data.find(b"\r\n")
        if nl <= 0:
            return 0
        line = data[:nl].decode("ascii", errors="ignore")
        parts = line.split(" ", 2)
        if len(parts) >= 2 and parts[1].isdigit():
            return int(parts[1])
        return 0

    @staticmethod
    def _parse_status(status_line):
        parts = status_line.decode("ascii", errors="ignore").split(" ", 2)
        if len(parts) >= 2 and parts[1].isdigit():
            return int(parts[1])
        return 0

    @staticmethod
    async def _write_response(writer, code, body):
        reason = {400: "Bad Request", 502: "Bad Gateway", 503: "Service Unavailable"}.get(
            code, "Error"
        )
        try:
            writer.write(f"HTTP/1.1 {code} {reason}\r\nContent-Length: {len(body)}\r\n\r\n".encode())
            writer.write(body)
            writer.write(b"\r\n")
            await writer.drain()
        except Exception:
            pass
        try:
            writer.close()
        except Exception:
            pass


def main():
    host = os.getenv("VIRTUAL_PROXY_HOST", "0.0.0.0")
    port = int(os.getenv("VIRTUAL_PROXY_PORT", "5010"))
    flask_host = os.getenv("FLASK_HOST", "127.0.0.1")
    flask_port = int(os.getenv("FLASK_PORT", "5010"))
    server = VirtualProxyServer(host, port, flask_host, flask_port)
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
