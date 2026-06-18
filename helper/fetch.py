# -*- coding: utf-8 -*-
"""
   fetch - 多线程代理采集
"""
__author__ = 'JHao'

import re
import json
import requests
from threading import Thread
from helper.proxy import Proxy
from helper.check import DoValidator
from handler.logHandler import LogHandler
from handler.proxyHandler import ProxyHandler
from fetcher.proxyFetcher import ProxyFetcher
from handler.configHandler import ConfigHandler
from handler.sourceHandler import SourceLoader


def generic_url_fetcher(source_config):
    """通用URL代理抓取器（用于AI发现的源）"""
    url = source_config.url
    method = source_config.method or 'text'
    try:
        resp = requests.get(url, timeout=15, verify=False,
                            headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()

        if method == 'json_api':
            data = resp.json()
            # 支持简单的json_path: data[*].ip / data[*].port
            items = data if isinstance(data, list) else data.get('data', data.get('proxies', []))
            for item in items:
                if isinstance(item, dict):
                    ip = item.get('ip', '')
                    port = item.get('port', '')
                    if ip and port:
                        yield f"{ip}:{port}"
                elif isinstance(item, str) and ':' in item:
                    yield item
        else:
            # text / html_regex: 按行分割+正则匹配
            ip_pattern = re.compile(r'(?:\d{1,3}\.){3}\d{1,3}:\d{2,5}')
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                matches = ip_pattern.findall(line)
                if matches:
                    for m in matches:
                        yield m
                elif ':' in line:
                    yield line
    except Exception:
        pass


class _ThreadFetcher(Thread):

    def __init__(self, fetch_source, proxy_dict, source_config=None):
        Thread.__init__(self)
        self.fetch_source = fetch_source
        self.proxy_dict = proxy_dict
        self.source_config = source_config
        self.log = LogHandler("fetcher")

        if source_config and source_config.type != 'builtin':
            self.fetcher = lambda: generic_url_fetcher(source_config)
        else:
            self.fetcher = getattr(ProxyFetcher, fetch_source, None)

    def run(self):
        self.log.info("ProxyFetch - {func}: start".format(func=self.fetch_source))
        total = 0
        accepted = 0
        try:
            for proxy in self.fetcher():
                total += 1
                proxy = proxy.strip()
                if not DoValidator.preValidator(proxy):
                    continue
                accepted += 1
                if proxy in self.proxy_dict:
                    self.proxy_dict[proxy].add_source(self.fetch_source)
                else:
                    self.proxy_dict[proxy] = Proxy(
                        proxy, source=self.fetch_source)
            self.log.info(
                "ProxyFetch - {func}: complete, accepted {accepted}/{total}".format(
                    func=self.fetch_source, accepted=accepted, total=total))
        except Exception as e:
            self.log.error("ProxyFetch - {func}: error".format(func=self.fetch_source))
            self.log.error(str(e))


class Fetcher(object):
    name = "fetcher"

    def __init__(self):
        self.log = LogHandler(self.name)
        self.conf = ConfigHandler()
        self.loader = SourceLoader()

    def run(self):
        """
        fetch proxy with proxyFetcher
        :return:
        """
        proxy_dict = dict()
        thread_list = list()
        self.log.info("ProxyFetch : start")

        for fetch_source in self.conf.fetchers:
            source_config = self.loader.get_source(fetch_source)

            if source_config and source_config.type != 'builtin':
                thread_list.append(_ThreadFetcher(fetch_source, proxy_dict, source_config))
                continue

            # builtin源：使用ProxyFetcher的静态方法
            fetcher = getattr(ProxyFetcher, fetch_source, None)
            if not fetcher:
                self.log.error("ProxyFetch - {func}: class method not exists!".format(func=fetch_source))
                continue
            if not callable(fetcher):
                self.log.error("ProxyFetch - {func}: must be class method".format(func=fetch_source))
                continue
            thread_list.append(_ThreadFetcher(fetch_source, proxy_dict))

        for thread in thread_list:
            thread.setDaemon(True)
            thread.start()

        for thread in thread_list:
            thread.join()

        self.log.info("ProxyFetch - all complete!")
        for _ in proxy_dict.values():
            yield _
