# -*- coding: utf-8 -*-
"""
   protocolParser - 解析 vmess/vless/trojan/ss/socks5 URI 及 Clash YAML / HTTP 订阅
   每个解析器返回统一格式: dict(scheme, host, port, uri, name)
"""
__author__ = 'JHao'

import re
import base64
import hashlib
from urllib.parse import urlparse, unquote, parse_qs

try:
    import yaml
except ImportError:
    yaml = None


def parse_proxy_uri(uri):
    """识别并解析代理 URI，返回 dict(scheme, host, port, uri, name) 或 None"""
    uri = uri.strip()
    if not uri:
        return None
    if uri.startswith("vmess://"):
        return _parse_vmess(uri)
    if uri.startswith("vless://"):
        return _parse_vless(uri)
    if uri.startswith("trojan://"):
        return _parse_trojan(uri)
    if uri.startswith("ss://"):
        return _parse_ss(uri)
    if uri.startswith("socks5://"):
        return _parse_socks5(uri)
    if uri.startswith("socks4://"):
        return _parse_socks5(uri, scheme="socks4")
    return None


def parse_clash_subscription(text):
    """解析 Clash YAML 订阅，从 proxies 段提取所有节点"""
    if yaml is None:
        return []
    try:
        data = yaml.safe_load(text)
    except Exception:
        return []
    if not isinstance(data, dict):
        return []
    proxies = data.get("proxies", [])
    if not isinstance(proxies, list):
        return []
    result = []
    for p in proxies:
        if not isinstance(p, dict):
            continue
        node = _clash_proxy_to_dict(p)
        if node:
            result.append(node)
    return result


def parse_http_subscription(text):
    """按行解析 base64/明文 URI 列表，返回 list[dict]"""
    text = text.strip()
    # 尝试整体 base64 解码
    try:
        decoded = base64.b64decode(text).decode("utf-8", errors="ignore")
        text = decoded
    except Exception:
        pass

    result = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # 尝试对单行 base64 解码
        try:
            decoded_line = base64.b64decode(line).decode("utf-8", errors="ignore")
            # 如果解码结果包含协议前缀，替换原行
            if any(decoded_line.startswith(p) for p in ("vmess://", "vless://", "trojan://", "ss://", "socks5://")):
                line = decoded_line
        except Exception:
            pass
        node = parse_proxy_uri(line)
        if node:
            result.append(node)
    return result


# ── 内部解析器 ──────────────────────────────────────────


def _parse_vmess(uri):
    """vmess://base64(JSON) → {v, ps, add, port, id, aid, net, type, host, path, tls}"""
    payload = uri[len("vmess://"):]
    # 部分实现可能再包一层 base64 padding
    try:
        decoded = base64.b64decode(_pad_b64(payload)).decode("utf-8", errors="ignore")
    except Exception:
        return None
    try:
        info = _safe_json(decoded)
    except Exception:
        return None
    if not info or not info.get("add") or not info.get("port"):
        return None
    host = info["add"]
    port = str(info["port"])
    name = info.get("ps", "") or f"{host}:{port}"
    return _make_node("vmess", host, port, uri, name)


def _parse_vless(uri):
    """vless://uuid@host:port?type=...&security=...&sni=...#name"""
    try:
        parsed = urlparse(uri)
    except Exception:
        return None
    host = parsed.hostname
    port = str(parsed.port or 443)
    if not host:
        return None
    name = unquote(parsed.fragment) if parsed.fragment else f"{host}:{port}"
    return _make_node("vless", host, port, uri, name)


def _parse_trojan(uri):
    """trojan://password@host:port?sni=...#name"""
    try:
        parsed = urlparse(uri)
    except Exception:
        return None
    host = parsed.hostname
    port = str(parsed.port or 443)
    if not host:
        return None
    name = unquote(parsed.fragment) if parsed.fragment else f"{host}:{port}"
    return _make_node("trojan", host, port, uri, name)


def _parse_ss(uri):
    """ss://base64(method:password)@host:port#name  (SIP002)"""
    payload = uri[len("ss://"):]
    name = ""
    if "#" in payload:
        payload, name_part = payload.rsplit("#", 1)
        name = unquote(name_part)
    # SIP002: method:password@host:port
    if "@" in payload:
        userinfo, hostport = payload.rsplit("@", 1)
        try:
            decoded_user = base64.b64decode(_pad_b64(userinfo)).decode("utf-8", errors="ignore")
        except Exception:
            decoded_user = userinfo
        # decoded_user = "method:password"
    else:
        # 旧格式: 整体 base64
        try:
            decoded = base64.b64decode(_pad_b64(payload)).decode("utf-8", errors="ignore")
        except Exception:
            return None
        if "@" not in decoded:
            return None
        decoded_user, hostport = decoded.rsplit("@", 1)

    # hostport 可能是 host:port 或 [ipv6]:port
    if hostport.startswith("["):
        bracket_end = hostport.find("]")
        if bracket_end < 0:
            return None
        host = hostport[1:bracket_end]
        port_str = hostport[bracket_end + 2:] if hostport[bracket_end:].startswith("]:") else ""
    else:
        parts = hostport.rsplit(":", 1)
        if len(parts) != 2:
            return None
        host, port_str = parts

    if not host or not port_str:
        return None
    port = port_str
    if not name:
        name = f"{host}:{port}"
    return _make_node("ss", host, port, uri, name)


def _parse_socks5(uri, scheme="socks5"):
    """socks5://[user:pass@]host:port"""
    try:
        parsed = urlparse(uri)
    except Exception:
        return None
    host = parsed.hostname
    port = str(parsed.port or 1080)
    if not host:
        return None
    name = f"{host}:{port}"
    return _make_node(scheme, host, port, uri, name)


# ── Clash proxy → 统一 dict ──────────────────────────────


_CLASH_TYPE_MAP = {
    "vmess": "vmess",
    "vless": "vless",
    "trojan": "trojan",
    "ss": "ss",
    "ssr": None,  # 不支持 SSR
    "socks5": "socks5",
    "socks4": "socks4",
    "http": "http",
}


def _clash_proxy_to_dict(p):
    """把 Clash proxies[] 中的一个条目转为 dict(scheme, host, port, uri, name)"""
    ptype = p.get("type", "").lower()
    scheme = _CLASH_TYPE_MAP.get(ptype)
    if scheme is None:
        return None
    host = p.get("server", "")
    port = p.get("port", "")
    if not host or not port:
        return None
    name = p.get("name", "") or f"{host}:{port}"
    # 反序列化为 URI（方便后续存储到 raw_uri）
    uri = _clash_proxy_to_uri(scheme, p)
    return _make_node(scheme, str(host), str(port), uri, name)


def _clash_proxy_to_uri(scheme, p):
    """从 Clash proxy 条目反序列化为 URI"""
    try:
        if scheme == "vmess":
            vmess_info = {
                "v": "2",
                "ps": p.get("name", ""),
                "add": p.get("server", ""),
                "port": p.get("port", ""),
                "id": p.get("uuid", ""),
                "aid": p.get("alterId", 0),
                "net": p.get("network", "tcp"),
                "type": p.get("network", "tcp"),
                "host": p.get("ws-opts", {}).get("headers", {}).get("Host", ""),
                "path": p.get("ws-opts", {}).get("path", "") or p.get("h2-opts", {}).get("path", ""),
                "tls": "tls" if p.get("tls") else "",
            }
            if p.get("servername"):
                vmess_info["sni"] = p["servername"]
            encoded = base64.b64encode(
                _json_compact(vmess_info).encode()
            ).decode()
            return f"vmess://{encoded}"
        if scheme == "vless":
            uuid = p.get("uuid", "")
            host = p.get("server", "")
            port = p.get("port", 443)
            params = []
            if p.get("network"):
                params.append(f"type={p['network']}")
            if p.get("tls"):
                params.append("security=tls")
            if p.get("servername"):
                params.append(f"sni={p['servername']}")
            if p.get("ws-opts"):
                ws = p["ws-opts"]
                if ws.get("path"):
                    params.append(f"path={ws['path']}")
                if ws.get("headers", {}).get("Host"):
                    params.append(f"host={ws['headers']['Host']}")
            frag = f"#{p.get('name', '')}" if p.get("name") else ""
            query = "&".join(params)
            return f"vless://{uuid}@{host}:{port}?{query}{frag}"
        if scheme == "trojan":
            password = p.get("password", "")
            host = p.get("server", "")
            port = p.get("port", 443)
            params = []
            if p.get("sni"):
                params.append(f"sni={p['sni']}")
            if p.get("network"):
                params.append(f"type={p['network']}")
            frag = f"#{p.get('name', '')}" if p.get("name") else ""
            query = "&".join(params)
            return f"trojan://{password}@{host}:{port}?{query}{frag}"
        if scheme == "ss":
            cipher = p.get("cipher", "")
            password = p.get("password", "")
            host = p.get("server", "")
            port = p.get("port", "")
            userinfo = base64.b64encode(f"{cipher}:{password}".encode()).decode()
            frag = f"#{p.get('name', '')}" if p.get("name") else ""
            return f"ss://{userinfo}@{host}:{port}{frag}"
        if scheme in ("socks5", "socks4"):
            host = p.get("server", "")
            port = p.get("port", 1080)
            username = p.get("username", "")
            password = p.get("password", "")
            auth = f"{username}:{password}@" if username and password else ""
            return f"{scheme}://{auth}{host}:{port}"
        if scheme == "http":
            host = p.get("server", "")
            port = p.get("port", 80)
            username = p.get("username", "")
            password = p.get("password", "")
            auth = f"{username}:{password}@" if username and password else ""
            return f"http://{auth}{host}:{port}"
    except Exception:
        pass
    return ""


# ── 工具函数 ────────────────────────────────────────────


def _make_node(scheme, host, port, uri, name):
    """构造统一节点 dict"""
    return {
        "scheme": scheme,
        "host": host,
        "port": port,
        "uri": uri,
        "name": name,
    }


def _pad_b64(s):
    """补齐 base64 padding"""
    missing = len(s) % 4
    if missing:
        s += "=" * (4 - missing)
    return s


def _safe_json(text):
    """安全解析 JSON，容错常见格式问题"""
    import json
    text = text.strip()
    if not text.startswith("{"):
        return None
    return json.loads(text)


def _json_compact(d):
    """紧凑 JSON 输出（无空格）"""
    import json
    return json.dumps(d, separators=(",", ":"), ensure_ascii=False)


def proxy_key(scheme, host, port, uri=""):
    """
    生成 Redis hash key:
    - http/https/socks5: host:port
    - 加密协议: scheme:host:port:md5(uri)[:8]
    """
    if scheme in ("http", "https", "socks5"):
        return f"{host}:{port}"
    uri_hash = hashlib.md5(uri.encode()).hexdigest()[:8] if uri else "00000000"
    return f"{scheme}:{host}:{port}:{uri_hash}"
