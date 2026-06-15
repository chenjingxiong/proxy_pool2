# -*- coding: utf-8 -*-
"""
-------------------------------------------------
   File Name：     virtualProxy
   Description :   虚拟代理服务器 — 对外暴露为单个 HTTP/HTTPS 代理，
                   内部自动从代理池挑选可用代理转发流量，
                   让外部应用无感使用代理池。
   date：          2026/06/16
-------------------------------------------------
"""

import os
import sys
import asyncio
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from handler.proxyHandler import ProxyHandler
from handler.configHandler import ConfigHandler

log = logging.getLogger("virtual_proxy")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)

MAX_RETRIES = int(os.getenv("VIRTUAL_PROXY_RETRIES", "3"))
CONNECT_TIMEOUT = 8
READ_TIMEOUT = 15
PIPE_BUF = 65536


class VirtualProxyServer:
    def __init__(self, host="0.0.0.0", port=5011):
        self.host = host
        self.port = port
        self.proxy_handler = ProxyHandler()

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
        log.info("VirtualProxyServer listening on %s", addrs)
        async with server:
            await server.serve_forever()

    async def _handle_client(self, reader, writer):
        addr = writer.get_extra_info("peername")
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
            await self._handle_connect(reader, writer, target, addr, head)
        else:
            await self._handle_http(reader, writer, target, addr, head)

    async def _handle_connect(self, reader, writer, target, addr, head):
        tried = set()
        for _ in range(MAX_RETRIES):
            proxy_obj = self._pick_proxy(exclude=tried)
            if not proxy_obj:
                break
            tried.add(proxy_obj.proxy)
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
                if b" 200 " in resp.split(b"\r\n", 1)[0]:
                    writer.write(b"HTTP/1.1 200 Connection established\r\n\r\n")
                    await writer.drain()
                    log.info("CONNECT %s via %s (%s)", target, proxy_obj.proxy, addr)
                    self._mark_used(proxy_obj)
                    await self._pipe_both(reader, writer, up_r, up_w)
                    return
                up_w.close()
            except Exception as exc:
                log.debug("CONNECT %s via %s err: %s", target, proxy_obj.proxy, exc)
                if up_w:
                    try:
                        up_w.close()
                    except Exception:
                        pass

        await self._write_response(writer, 502, b"Bad Gateway")

    async def _handle_http(self, reader, writer, target, addr, head):
        tried = set()
        for _ in range(MAX_RETRIES):
            proxy_obj = self._pick_proxy(exclude=tried)
            if not proxy_obj:
                break
            tried.add(proxy_obj.proxy)
            up_r, up_w = None, None
            try:
                ph, pp = proxy_obj.proxy.rsplit(":", 1)
                up_r, up_w = await asyncio.wait_for(
                    asyncio.open_connection(ph, int(pp)), timeout=CONNECT_TIMEOUT
                )
                up_w.write(head)
                await up_w.drain()
                log.info("HTTP %s via %s (%s)", target[:60], proxy_obj.proxy, addr)
                self._mark_used(proxy_obj)
                await self._pipe_both(reader, writer, up_r, up_w)
                return
            except Exception as exc:
                log.debug("HTTP %s via %s err: %s", target[:60], proxy_obj.proxy, exc)
                if up_w:
                    try:
                        up_w.close()
                    except Exception:
                        pass

        await self._write_response(writer, 502, b"Bad Gateway")

    async def _pipe_both(self, c_r, c_w, u_r, u_w):
        async def forward(src, dst):
            try:
                while True:
                    data = await src.read(PIPE_BUF)
                    if not data:
                        break
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
            forward(u_r, c_w),
            return_exceptions=True,
        )

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
