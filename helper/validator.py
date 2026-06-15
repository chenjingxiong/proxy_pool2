# -*- coding: utf-8 -*-
"""
-------------------------------------------------
   File Name：     _validators
   Description :   定义proxy验证方法
   Author :        JHao
   date：          2021/5/25
-------------------------------------------------
   Change Activity:
                   2023/03/10: 支持带用户认证的代理格式 username:password@ip:port
                   2025/04/24: 添加UA轮换、多验证URL、连接/读取超时分离
                   2026/06/15: 真实URL验证 — GET访问真实网站，任一成功即通过
-------------------------------------------------
"""
__author__ = 'JHao'

import re
import random
from requests import get
from util.six import withMetaclass
from util.singleton import Singleton
from handler.configHandler import ConfigHandler

conf = ConfigHandler()

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:34.0) Gecko/20100101 Firefox/34.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0',
]

HEADER = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Connection': 'keep-alive',
    'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
}

IP_REGEX = re.compile(r"(.*:.*@)?\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}")

# HTTP验证目标：GET访问，任一返回200即通过
HTTP_VALIDATE_URLS = [
    "http://www.baidu.com",
    "http://myip.ipip.net",
]

# HTTPS验证目标：GET访问，任一返回200即通过
HTTPS_VALIDATE_URLS = [
    "https://www.baidu.com",
    "https://api.ipify.org",
]


def _get_random_headers():
    headers = HEADER.copy()
    headers['User-Agent'] = random.choice(USER_AGENTS)
    return headers


def _get_timeout():
    """
    Return a (connect_timeout, read_timeout) tuple.
    connect_timeout is shorter to quickly reject unreachable proxies.
    """
    base_timeout = conf.verifyTimeout
    connect_timeout = max(base_timeout // 2, 3)
    read_timeout = base_timeout
    return (connect_timeout, read_timeout)


def _extract_proxy_ip(proxy):
    """从代理字符串中提取 IP 地址，支持 user:pass@ip:port 格式"""
    return proxy.split('@')[-1].split(':')[0]


class ProxyValidator(withMetaclass(Singleton)):
    pre_validator = []
    http_validator = []
    https_validator = []

    @classmethod
    def addPreValidator(cls, func):
        cls.pre_validator.append(func)
        return func

    @classmethod
    def addHttpValidator(cls, func):
        cls.http_validator.append(func)
        return func

    @classmethod
    def addHttpsValidator(cls, func):
        cls.https_validator.append(func)
        return func


@ProxyValidator.addPreValidator
def formatValidator(proxy):
    """检查代理格式"""
    return True if IP_REGEX.fullmatch(proxy) else False


@ProxyValidator.addHttpValidator
def httpTimeOutValidator(proxy):
    """HTTP验证：GET访问真实网站，任一返回200即通过"""
    proxies = {"http": "http://{proxy}".format(proxy=proxy),
               "https": "http://{proxy}".format(proxy=proxy)}
    headers = _get_random_headers()
    timeout = _get_timeout()

    for url in HTTP_VALIDATE_URLS:
        try:
            r = get(url, headers=headers, proxies=proxies, timeout=timeout)
            if r.status_code == 200:
                return True
        except Exception:
            continue
    return False


@ProxyValidator.addHttpsValidator
def httpsTimeOutValidator(proxy):
    """HTTPS验证：GET访问真实HTTPS网站，任一返回200即通过"""
    proxies = {"http": "http://{proxy}".format(proxy=proxy),
               "https": "https://{proxy}".format(proxy=proxy)}
    headers = _get_random_headers()
    timeout = _get_timeout()

    for url in HTTPS_VALIDATE_URLS:
        try:
            r = get(url, headers=headers, proxies=proxies,
                    timeout=timeout, verify=False)
            if r.status_code == 200:
                return True
        except Exception:
            continue
    return False
