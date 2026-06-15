# -*- coding: utf-8 -*-
"""
-------------------------------------------------
   File Name：     virtualProxy
   Description :   虚拟代理服务器 — 对外暴露为单个 HTTP/HTTPS 代理，
                   内部自动从代理池挑选可用代理转发流量，
                   让外部应用无感使用代理池。
                   每次外部调用记录审计日志（成功/失败、代理IP、状态码、目标URL等）。
   date：          2026/06/16
-------------------------------------------------
"""

import os
import sys
import time
import asyncio
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from handler.proxyHandler import ProxyHandler
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
    def __init__(self, host="0.0.0.0", port=5011):
        self.host = host
        self.port = port
        self.proxy_handler = ProxyHandler()
        self.audit = AuditLogger(
            file_path=AUDIT_FILE,
            max_size_kb=AUDIT_SIZE_KB,
            backup_count=AUDIT_BACKUP_COUNT,
        )

    def _pick_proxy(self, exclude=None):
        for _ in range(5):
            proxy = self.proxy_handler.get()
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
            "VirtualProxyServer listening on %s | audit=%s size=%dKB",
            addrs, AUDIT_FILE, AUDIT_SIZE_KB,
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
        else:
            await self._handle_http(reader, writer, method, target, client_str, head)

    async def _handle_connect(self, reader, writer, target, client_str, head):
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
            up_r, up_w = None, None
            try:
                ph, pp = proxy_obj.proxy.rsplit(":", 1)
                up_r, up_w = await asyncio.wait_for(
                    asyncio.open_connection(ph, int(pp)), timeout=CONNECT_TIMEOUT
                )
                up_w.write(
                    f"CONNECT {target} HTTP/1.1\r\nHost: {target}\r\n\r\n".encode()
                )
                await up_w.drain()

                resp = await asyncio.wait_for(
                    up_r.readuntil(b"\r\n\r\n"), timeout=READ_TIMEOUT
                )
                status_line = resp.split(b"\r\n", 1)[0]
                if b" 200 " in status_line:
                    writer.write(b"HTTP/1.1 200 Connection established\r\n\r\n")
                    await writer.drain()
                    log.info("CONNECT %s via %s (%s)", target, proxy_obj.proxy, client_str)
                    self._mark_used(proxy_obj)
                    await self._pipe(reader, writer, up_r, up_w, capture_status=False)
                    duration = round(time.time() - start, 3)
                    self.audit.log(client_str, "CONNECT", target, proxy_obj.proxy,
                                   True, 200, duration)
                    return
                status_code = self._parse_status(status_line)
                last_error = f"upstream {status_line.decode(errors='ignore')}"
                up_w.close()
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                log.debug("CONNECT %s via %s err: %s", target, proxy_obj.proxy, exc)
                if up_w:
                    try:
                        up_w.close()
                    except Exception:
                        pass

        duration = round(time.time() - start, 3)
        self.audit.log(client_str, "CONNECT", target, last_proxy,
                       False, 502, duration, error=last_error)
        await self._write_response(writer, 502, b"Bad Gateway")

    async def _handle_http(self, reader, writer, method, target, client_str, head):
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
            up_r, up_w = None, None
            try:
                ph, pp = proxy_obj.proxy.rsplit(":", 1)
                up_r, up_w = await asyncio.wait_for(
                    asyncio.open_connection(ph, int(pp)), timeout=CONNECT_TIMEOUT
                )
                up_w.write(head)
                await up_w.drain()
                log.info("HTTP %s %s via %s (%s)", method, target[:60], proxy_obj.proxy, client_str)
                self._mark_used(proxy_obj)
                status = await self._pipe(reader, writer, up_r, up_w, capture_status=True)
                duration = round(time.time() - start, 3)
                # status=0 表示未收到有效 HTTP 响应（上游异常关闭/发回非 HTTP 数据），视为失败
                success = status > 0
                self.audit.log(client_str, method, target, proxy_obj.proxy,
                               success, status, duration,
                               error="" if success else "no valid http response")
                return
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                log.debug("HTTP %s via %s err: %s", target[:60], proxy_obj.proxy, exc)
                if up_w:
                    try:
                        up_w.close()
                    except Exception:
                        pass

        duration = round(time.time() - start, 3)
        self.audit.log(client_str, method, target, last_proxy,
                       False, 502, duration, error=last_error)
        await self._write_response(writer, 502, b"Bad Gateway")

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
    port = int(os.getenv("VIRTUAL_PROXY_PORT", "5011"))
    server = VirtualProxyServer(host, port)
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
