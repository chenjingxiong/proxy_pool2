# -*- coding: utf-8 -*-
"""
   mihomoHandler - 与 mihomo (Clash.Meta) sidecar 交互
   - generate_config_yaml: 从池中的加密协议节点生成 Clash 配置
   - reload_config: 通过 API 热加载配置
   - test_proxy: 通过 selector 切换节点测试延迟
   - switch_selector: 切换 pool-selector 当前激活的节点
"""
__author__ = 'JHao'

import logging
import threading
import base64
import json as _json
from urllib.parse import urlparse, parse_qs, unquote, quote

import requests

from handler.configHandler import ConfigHandler

log = logging.getLogger("mihomo")

SELECTOR_NAME = "pool-selector"
DIRECT_NAME = "DIRECT"


class MihomoClient(object):

    def __init__(self):
        self.conf = ConfigHandler()
        self.api_url = self.conf.mihomoApiUrl
        self.socks_host = self.conf.mihomoSocksHost
        self.socks_port = self.conf.mihomoSocksPort
        self._lock = threading.Lock()
        self._timeout = 5

    # ==================== 配置生成 ====================

    def generate_config_yaml(self, proxies):
        """
        从池中的代理节点生成 Clash 配置字典
        proxies: list[Proxy]
        """
        try:
            import yaml
        except ImportError:
            log.error("PyYAML not installed; cannot generate mihomo config")
            return ""

        clash_proxies = []
        names = set()
        for p in proxies:
            if p.scheme in ("vmess", "vless", "trojan", "ss") and p.raw_uri:
                entry = _uri_to_clash_entry(p.raw_uri, p.scheme)
            elif p.scheme in ("http", "https", "socks5"):
                entry = _proxy_to_clash_entry(p)
            else:
                continue
            if not entry:
                continue
            name = _unique_name(entry.get("name") or "node", names)
            entry["name"] = name
            names.add(name)
            clash_proxies.append(entry)

        proxy_names = [p["name"] for p in clash_proxies] or [DIRECT_NAME]
        config = {
            "mixed-port": 7890,
            "external-controller": "0.0.0.0:9090",
            "proxies": clash_proxies,
            "proxy-groups": [
                {
                    "name": SELECTOR_NAME,
                    "type": "select",
                    "proxies": proxy_names,
                }
            ],
            "rules": [f"MATCH,{SELECTOR_NAME}"],
        }
        return yaml.safe_dump(config, allow_unicode=True, sort_keys=False)

    # ==================== API 调用 ====================

    def reload_config(self, yaml_str):
        """通过 PUT /configs?force=true 热加载配置"""
        if not yaml_str:
            return False
        url = f"{self.api_url}/configs?force=true"
        try:
            # mihomo 支持直接传 payload（无需文件）
            resp = requests.put(
                url,
                json={"payload": yaml_str},
                timeout=self._timeout,
            )
            if resp.status_code in (200, 204):
                log.info("mihomo config reloaded")
                return True
            log.warning("mihomo reload failed: %s %s", resp.status_code, resp.text[:200])
            return False
        except Exception as exc:
            log.warning("mihomo reload err: %s", exc)
            return False

    def switch_selector(self, proxy_name):
        """PUT /proxies/pool-selector {name: proxy_name}"""
        url = f"{self.api_url}/proxies/{quote(SELECTOR_NAME)}"
        try:
            resp = requests.put(url, json={"name": proxy_name}, timeout=self._timeout)
            return resp.status_code in (200, 204)
        except Exception as exc:
            log.debug("mihomo switch_selector err: %s", exc)
            return False

    def test_proxy(self, proxy_name, test_url=None):
        """GET /proxies/{name}/delay?url=... 测延迟（毫秒）"""
        test_url = test_url or self.conf.mihomoTestUrl
        url = f"{self.api_url}/proxies/{quote(proxy_name)}/delay"
        try:
            resp = requests.get(url, params={"url": test_url}, timeout=self._timeout)
            if resp.status_code == 200:
                data = resp.json()
                delay = data.get("delay")
                if isinstance(delay, (int, float)) and delay > 0:
                    return int(delay)
            return 0
        except Exception:
            return 0

    def list_proxies(self):
        """GET /proxies 返回当前 mihomo 配置"""
        url = f"{self.api_url}/proxies"
        try:
            resp = requests.get(url, timeout=self._timeout)
            if resp.status_code == 200:
                return resp.json().get("proxies", {})
        except Exception as exc:
            log.debug("mihomo list_proxies err: %s", exc)
        return {}

    def is_available(self):
        """mihomo API 是否可达"""
        try:
            resp = requests.get(f"{self.api_url}/version", timeout=2)
            return resp.status_code == 200
        except Exception:
            return False


# ==================== 工具函数 ====================


def _proxy_to_clash_entry(proxy):
    host, _, port = proxy.proxy.partition(":")
    try:
        port_int = int(port)
    except ValueError:
        return None
    return {
        "name": f"{host}:{port}",
        "type": "socks5" if proxy.scheme == "socks5" else "http",
        "server": host,
        "port": port_int,
    }


def _uri_to_clash_entry(uri, scheme):
    """把加密协议 URI 转为 Clash proxy 条目"""
    try:
        if scheme == "vmess":
            payload = uri[len("vmess://"):]
            missing = len(payload) % 4
            if missing:
                payload += "=" * (4 - missing)
            info = _json.loads(base64.b64decode(payload).decode("utf-8", errors="ignore"))
            entry = {
                "name": info.get("ps", "") or f"{info.get('add')}:{info.get('port')}",
                "type": "vmess",
                "server": info.get("add", ""),
                "port": int(info.get("port", 0)),
                "uuid": info.get("id", ""),
                "alterId": int(info.get("aid", 0) or 0),
                "cipher": info.get("scy", "auto") or "auto",
                "network": info.get("net", "tcp") or "tcp",
            }
            if info.get("tls"):
                entry["tls"] = True
                if info.get("sni"):
                    entry["servername"] = info["sni"]
            if entry["network"] == "ws":
                ws_opts = {}
                if info.get("path"):
                    ws_opts["path"] = info["path"]
                if info.get("host"):
                    ws_opts["headers"] = {"Host": info["host"]}
                if ws_opts:
                    entry["ws-opts"] = ws_opts
            return entry
        if scheme == "vless":
            p = urlparse(uri)
            q = {k: v[0] for k, v in parse_qs(p.query).items()}
            entry = {
                "name": unquote(p.fragment) or f"{p.hostname}:{p.port}",
                "type": "vless",
                "server": p.hostname,
                "port": p.port or 443,
                "uuid": p.username or "",
                "network": q.get("type", "tcp"),
            }
            if q.get("security") == "tls":
                entry["tls"] = True
            if q.get("sni"):
                entry["servername"] = q["sni"]
            if entry["network"] == "ws":
                ws_opts = {}
                if q.get("path"):
                    ws_opts["path"] = q["path"]
                if q.get("host"):
                    ws_opts["headers"] = {"Host": q["host"]}
                if ws_opts:
                    entry["ws-opts"] = ws_opts
            return entry
        if scheme == "trojan":
            p = urlparse(uri)
            q = {k: v[0] for k, v in parse_qs(p.query).items()}
            entry = {
                "name": unquote(p.fragment) or f"{p.hostname}:{p.port}",
                "type": "trojan",
                "server": p.hostname,
                "port": p.port or 443,
                "password": p.username or "",
            }
            if q.get("sni"):
                entry["sni"] = q["sni"]
            if q.get("type"):
                entry["network"] = q["type"]
            return entry
        if scheme == "ss":
            p = urlparse(uri)
            userinfo = p.username or ""
            try:
                decoded = base64.b64decode(userinfo + "==").decode("utf-8", errors="ignore")
            except Exception:
                decoded = userinfo
            if ":" not in decoded:
                return None
            cipher, password = decoded.split(":", 1)
            return {
                "name": unquote(p.fragment) or f"{p.hostname}:{p.port}",
                "type": "ss",
                "server": p.hostname,
                "port": p.port,
                "cipher": cipher,
                "password": password,
            }
    except Exception as exc:
        log.debug("_uri_to_clash_entry err: %s", exc)
    return None


def _unique_name(base, existing):
    if base not in existing:
        return base
    i = 1
    while f"{base}-{i}" in existing:
        i += 1
    return f"{base}-{i}"
