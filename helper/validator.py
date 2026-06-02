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
-------------------------------------------------
"""
__author__ = 'JHao'

import re
import random
from requests import head
from util.six import withMetaclass
from util.singleton import Singleton
from handler.configHandler import ConfigHandler

conf = ConfigHandler()

# User-Agent pool for rotation
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

# Multiple validation target URLs for HTTP
HTTP_VALIDATE_URLS = [
    "http://httpbin.org",
    "http://www.baidu.com",
    "http://www.google.com",
    "https://httpbin.org/ip",
]

# Multiple validation target URLs for HTTPS
HTTPS_VALIDATE_URLS = [
    "https://www.qq.com",
    "https://www.baidu.com",
    "https://httpbin.org/ip",
    "https://www.google.com",
]

HEADER = {
    'Accept': '*/*',
    'Connection': 'keep-alive',
    'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
}

IP_REGEX = re.compile(r"(.*:.*@)?\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}")


def _get_random_headers():
    """Return headers with a randomly selected User-Agent."""
    headers = HEADER.copy()
    headers['User-Agent'] = random.choice(USER_AGENTS)
    return headers


def _get_timeout():
    """
    Return a (connect_timeout, read_timeout) tuple.
    connect_timeout is shorter to quickly reject unreachable proxies.
    read_timeout allows more time for data transfer.
    """
    base_timeout = conf.verifyTimeout
    connect_timeout = max(base_timeout // 2, 3)
    read_timeout = base_timeout
    return (connect_timeout, read_timeout)


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
    """ http检测超时 - 尝试多个验证URL，使用分离的连接/读取超时 """
    proxies = {"http": "http://{proxy}".format(proxy=proxy),
               "https": "http://{proxy}".format(proxy=proxy)}
    headers = _get_random_headers()
    timeout = _get_timeout()
    validate_urls = [conf.httpUrl] + [u for u in HTTP_VALIDATE_URLS if u != conf.httpUrl]

    for url in validate_urls:
        try:
            r = head(url, headers=headers, proxies=proxies, timeout=timeout)
            if r.status_code == 200:
                return True
        except Exception:
            continue
    return False


@ProxyValidator.addHttpsValidator
def httpsTimeOutValidator(proxy):
    """https检测超时 - 尝试多个验证URL，使用分离的连接/读取超时"""
    proxies = {"http": "http://{proxy}".format(proxy=proxy),
               "https": "https://{proxy}".format(proxy=proxy)}
    headers = _get_random_headers()
    timeout = _get_timeout()
    validate_urls = [conf.httpsUrl] + [u for u in HTTPS_VALIDATE_URLS if u != conf.httpsUrl]

    for url in validate_urls:
        try:
            r = head(url, headers=headers, proxies=proxies, timeout=timeout, verify=False)
            if r.status_code == 200:
                return True
        except Exception:
            continue
    return False


@ProxyValidator.addHttpValidator
def customValidatorExample(proxy):
    """自定义validator函数，校验代理是否可用, 返回True/False"""
    return True
