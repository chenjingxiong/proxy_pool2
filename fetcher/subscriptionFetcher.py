# -*- coding: utf-8 -*-
"""
   subscriptionFetcher - 抓取并解析订阅/单节点
   支持 4 种 source.type:
     - subscription  : HTTP/TXT 订阅 URL（base64/明文混排）
     - clash_yaml    : Clash YAML 订阅 URL
     - single_node   : 单节点 URI 直接粘贴
     - plain_uri_list: 多行 URI 直接粘贴
   每个 fetcher 返回 generator[Proxy]
"""
__author__ = 'JHao'

import logging

import requests

from helper.proxy import Proxy
from helper.protocolParser import (
    parse_proxy_uri,
    parse_clash_subscription,
    parse_http_subscription,
    proxy_key,
)

log = logging.getLogger("subscription_fetcher")

DEFAULT_TIMEOUT = 15
DEFAULT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def _fetch_url(url):
    """抓取订阅 URL 内容，返回文本或空串"""
    try:
        resp = requests.get(
            url,
            timeout=DEFAULT_TIMEOUT,
            verify=False,
            headers={"User-Agent": DEFAULT_UA},
        )
        resp.raise_for_status()
        return resp.text or ""
    except Exception as exc:
        log.warning("fetch_subscription url=%s err: %s", url, exc)
        return ""


def _node_to_proxy(node, source_name):
    """把 protocolParser 返回的 dict 转为 Proxy 对象"""
    scheme = node["scheme"]
    host = node["host"]
    port = str(node["port"])
    uri = node.get("uri", "")
    proxy_str = f"{host}:{port}"
    key = proxy_key(scheme, host, port, uri)
    return Proxy(
        proxy=key,
        source=source_name,
        scheme=scheme,
        raw_uri=uri,
    )


def fetch_subscription(source_config):
    """
    根据 SourceConfig 抓取订阅，yield Proxy 对象
    source_config 字段使用: type, url, content
    """
    src_type = source_config.type
    name = source_config.name

    nodes = []

    if src_type == "single_node":
        # content 字段存的是单条 URI
        content = getattr(source_config, "content", "") or ""
        node = parse_proxy_uri(content)
        if node:
            nodes.append(node)

    elif src_type == "plain_uri_list":
        content = getattr(source_config, "content", "") or ""
        nodes = parse_http_subscription(content)

    elif src_type == "subscription":
        url = source_config.url or ""
        if not url:
            return
        text = _fetch_url(url)
        if text:
            nodes = parse_http_subscription(text)

    elif src_type == "clash_yaml":
        url = source_config.url or ""
        if not url:
            return
        text = _fetch_url(url)
        if text:
            nodes = parse_clash_subscription(text)

    else:
        log.warning("unknown subscription type: %s", src_type)
        return

    for node in nodes:
        try:
            yield _node_to_proxy(node, name)
        except Exception as exc:
            log.debug("node_to_proxy err: %s", exc)
            continue
