# -*- coding: utf-8 -*-
"""
-------------------------------------------------
   File Name：     refreshHandler.py
   Description :   代理池自动刷新处理器
   当代理池数量低于阈值时自动触发抓取
-------------------------------------------------
   Change Activity:
                   2026/04/24: 代理自动刷新机制
-------------------------------------------------
"""
__author__ = 'proxy_pool'

from util.six import Queue
from helper.fetch import Fetcher
from helper.check import Checker
from handler.logHandler import LogHandler
from handler.proxyHandler import ProxyHandler
from handler.configHandler import ConfigHandler


class RefreshHandler(object):
    """ Proxy pool auto-refresh handler """

    def __init__(self):
        self.log = LogHandler("refresh")
        self.conf = ConfigHandler()
        self.proxy_handler = ProxyHandler()

    def getProxyCount(self):
        """
        get current proxy count in pool
        :return: int
        """
        count_info = self.proxy_handler.getCount()
        return count_info.get('count', {}).get('total', 0)

    def needRefresh(self, threshold=None):
        """
        check if proxy pool needs refresh
        :param threshold: custom threshold, defaults to poolSizeMin from config
        :return: bool
        """
        if threshold is None:
            threshold = self.conf.poolSizeMin
        current_count = self.getProxyCount()
        self.log.info('RefreshCheck - current: {count}, threshold: {threshold}'.format(
            count=current_count, threshold=threshold))
        return current_count < threshold

    def refresh(self):
        """
        fetch new proxies and validate them
        :return: number of new proxies fetched
        """
        self.log.info('ProxyRefresh: starting fetch...')
        proxy_queue = Queue()
        proxy_fetcher = Fetcher()

        count = 0
        for proxy in proxy_fetcher.run():
            proxy_queue.put(proxy)
            count += 1

        self.log.info('ProxyRefresh: fetched {count} raw proxies, validating...'.format(count=count))
        Checker("raw", proxy_queue)
        self.log.info('ProxyRefresh: validation complete')

        new_count = self.getProxyCount()
        self.log.info('ProxyRefresh: pool now has {count} proxies'.format(count=new_count))
        return new_count

    def checkAndRefresh(self, threshold=None):
        """
        check proxy pool size and refresh if below threshold
        :param threshold: custom threshold
        :return: True if refreshed, False if not needed
        """
        if self.needRefresh(threshold):
            self.log.info('ProxyRefresh: pool below threshold, triggering refresh')
            self.refresh()
            return True
        else:
            self.log.info('ProxyRefresh: pool healthy, no refresh needed')
            return False


def runRefreshJob():
    """
    callable for scheduler to run refresh check
    can be added to scheduler as a scheduled job
    """
    handler = RefreshHandler()
    handler.checkAndRefresh()
