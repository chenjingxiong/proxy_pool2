# -*- coding: utf-8 -*-
"""
-------------------------------------------------
   File Name：     check
   Description :   执行代理校验
   Author :        JHao
   date：          2019/8/6
-------------------------------------------------
   Change Activity:
                   2019/08/06: 执行代理校验
                   2021/05/25: 分别校验http和https
                   2022/08/16: 获取代理Region信息
-------------------------------------------------
"""
__author__ = 'JHao'

import time
from util.six import Empty
from threading import Thread
from datetime import datetime
from util.webRequest import WebRequest
from handler.logHandler import LogHandler
from helper.proxy import Proxy, SCHEMES_ENCRYPTED
from helper.validator import ProxyValidator
from handler.proxyHandler import ProxyHandler
from handler.configHandler import ConfigHandler


class DoValidator(object):
    """ 执行校验 """

    conf = ConfigHandler()

    @classmethod
    def validator(cls, proxy, work_type):
        """
        校验入口 — 按 scheme 分发
        Args:
            proxy: Proxy Object
            work_type: raw/use
        Returns:
            Proxy Object
        """
        # 加密协议（vmess/vless/trojan/ss）：跳过 HTTP 验证
        # 标记为 last_status=None，由 mihomo 同步任务负责实际测速
        if proxy.scheme in SCHEMES_ENCRYPTED:
            proxy.check_count += 1
            proxy.last_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            proxy.last_status = None  # None = 待激活
            proxy.speed = 0.0
            proxy.https = True
            return proxy

        start_time = time.time()
        if proxy.scheme == "socks5":
            # SOCKS5：用 socks5 验证器，分别测 http 与 https 出口
            http_r = cls.socks5Validator(proxy)
            elapsed = time.time() - start_time
            https_r = http_r  # SOCKS5 验证已包含 HTTPS 目标
            if http_r:
                elapsed = time.time() - start_time
        else:
            # HTTP/HTTPS：原逻辑
            http_r = cls.httpValidator(proxy)
            elapsed = time.time() - start_time
            https_r = False if not http_r else cls.httpsValidator(proxy)
            if https_r:
                elapsed = time.time() - start_time

        proxy.check_count += 1
        proxy.last_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        proxy.last_status = True if http_r else False
        if http_r:
            proxy.speed = round(elapsed, 3)
            if proxy.fail_count > 0:
                proxy.fail_count -= 1
            proxy.https = True if https_r else False
            if work_type == "raw":
                proxy.region = cls.regionGetter(proxy) if cls.conf.proxyRegion else ""
        else:
            proxy.fail_count += 1
            proxy.speed = 0.0
        return proxy

    @classmethod
    def httpValidator(cls, proxy):
        for func in ProxyValidator.http_validator:
            if not func(proxy.proxy):
                return False
        return True

    @classmethod
    def httpsValidator(cls, proxy):
        for func in ProxyValidator.https_validator:
            if not func(proxy.proxy):
                return False
        return True

    @classmethod
    def socks5Validator(cls, proxy):
        for func in ProxyValidator.socks5_validator:
            if not func(proxy.proxy):
                return False
        return True

    @classmethod
    def preValidator(cls, proxy):
        for func in ProxyValidator.pre_validator:
            if not func(proxy):
                return False
        return True

    @classmethod
    def regionGetter(cls, proxy):
        try:
            url = 'https://searchplugin.csdn.net/api/v1/ip/get?ip=%s' % proxy.proxy.split(':')[0]
            r = WebRequest().get(url=url, retry_time=1, timeout=2).json
            return r['data']['address']
        except:
            return 'error'


class _ThreadChecker(Thread):
    """ 多线程检测 """

    def __init__(self, work_type, target_queue, thread_name):
        Thread.__init__(self, name=thread_name)
        self.work_type = work_type
        self.log = LogHandler("checker")
        self.proxy_handler = ProxyHandler()
        self.target_queue = target_queue
        self.conf = ConfigHandler()

    def run(self):
        self.log.info("{}ProxyCheck - {}: start".format(self.work_type.title(), self.name))
        while True:
            try:
                proxy = self.target_queue.get(block=False)
            except Empty:
                self.log.info("{}ProxyCheck - {}: complete".format(self.work_type.title(), self.name))
                break
            proxy = DoValidator.validator(proxy, self.work_type)
            if self.work_type == "raw":
                self.__ifRaw(proxy)
            else:
                self.__ifUse(proxy)
            self.target_queue.task_done()

    def __ifRaw(self, proxy):
        if proxy.last_status is False:
            self.log.info('RawProxyCheck - {}: {} fail'.format(self.name, proxy.proxy.ljust(23)))
            return
        # last_status 为 True 或 None（加密协议待激活）都允许入库
        if self.proxy_handler.putIfNotExists(proxy):
            status_text = "pass" if proxy.last_status else "pending"
            self.log.info('RawProxyCheck - {}: {} {}'.format(self.name, proxy.proxy.ljust(23), status_text))
        else:
            self.log.info('RawProxyCheck - {}: {} exist, skipped'.format(self.name, proxy.proxy.ljust(23)))

    def __ifUse(self, proxy):
        if proxy.last_status is False:
            if proxy.fail_count > self.conf.maxFailCount:
                self.log.info('UseProxyCheck - {}: {} fail, count {} delete'.format(self.name,
                                                                                    proxy.proxy.ljust(23),
                                                                                    proxy.fail_count))
                self.proxy_handler.delete(proxy)
            else:
                self.log.info('UseProxyCheck - {}: {} fail, count {} keep'.format(self.name,
                                                                                  proxy.proxy.ljust(23),
                                                                                  proxy.fail_count))
                self.proxy_handler.put(proxy)
            return
        # last_status 为 True 或 None（加密协议待激活）都保留
        status_text = "pass" if proxy.last_status else "pending"
        self.log.info('UseProxyCheck - {}: {} {}'.format(self.name, proxy.proxy.ljust(23), status_text))
        self.proxy_handler.put(proxy)


def Checker(tp, queue):
    """
    run Proxy ThreadChecker
    :param tp: raw/use
    :param queue: Proxy Queue
    :return:
    """
    thread_list = list()
    # 10 个并发足以打满网络验证瓶颈；过多会同时持有 resp.text 与 TLS 连接池，导致内存膨胀
    for index in range(10):
        thread_list.append(_ThreadChecker(tp, queue, "thread_%s" % str(index).zfill(2)))

    for thread in thread_list:
        thread.setDaemon(True)
        thread.start()

    for thread in thread_list:
        thread.join()
