# -*- coding: utf-8 -*-
"""
-------------------------------------------------
   File Name：     ProxyHandler.py
   Description :
   Author :       JHao
   date：          2016/12/3
-------------------------------------------------
   Change Activity:
                   2016/12/03:
                   2020/05/26: 区分http和https
-------------------------------------------------
"""
__author__ = 'JHao'

from helper.proxy import Proxy
from db.dbClient import DbClient
from handler.configHandler import ConfigHandler


class ProxyHandler(object):
    """ Proxy CRUD operator"""

    def __init__(self):
        self.conf = ConfigHandler()
        self.db = DbClient(self.conf.dbConn)
        self.db.changeTable(self.conf.tableName)

    def get(self, https=False):
        """
        return a proxy
        Args:
            https: True/False
        Returns:
        """
        proxy = self.db.get(https)
        return Proxy.createFromJson(proxy) if proxy else None

    def pop(self, https):
        """
        return and delete a useful proxy
        :return:
        """
        proxy = self.db.pop(https)
        if proxy:
            return Proxy.createFromJson(proxy)
        return None

    def put(self, proxy):
        """
        put proxy into use proxy (insert or update)
        :return:
        """
        self.db.put(proxy)

    def putIfNotExists(self, proxy):
        """
        put proxy into pool only if not exists (deduplication)
        :param proxy: Proxy obj
        :return: True if inserted, False if already exists
        """
        if self.exists(proxy):
            return False
        self.db.put(proxy)
        return True

    def delete(self, proxy):
        """
        delete useful proxy
        :param proxy:
        :return:
        """
        return self.db.delete(proxy.proxy)

    def getAll(self, https=False):
        """
        get all proxy from pool as Proxy list
        :return:
        """
        proxies = self.db.getAll(https)
        return [Proxy.createFromJson(_) for _ in proxies]

    def exists(self, proxy):
        """
        check proxy exists
        :param proxy:
        :return:
        """
        return self.db.exists(proxy.proxy)

    def getCount(self):
        """
        return raw_proxy and use_proxy count
        :return:
        """
        total_use_proxy = self.db.getCount()
        return {'count': total_use_proxy}

    def incrementUseCount(self, proxy):
        """
        increment proxy use_count by 1
        :param proxy: Proxy obj
        :return:
        """
        proxy.use_count = proxy.use_count + 1
        self.db.put(proxy)

    def getUseCountRanking(self, limit=10):
        """
        return proxy ranking sorted by use_count (descending)
        :param limit: number of proxies to return
        :return:
        """
        proxies = self.getAll()
        proxies.sort(key=lambda p: p.use_count, reverse=True)
        return proxies[:limit]
