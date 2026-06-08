# -*- coding: utf-8 -*-
"""
-------------------------------------------------
   File Name：     configHandler
   Description :
   Author :        JHao
   date：          2020/6/22
-------------------------------------------------
   Change Activity:
                   2020/6/22:
-------------------------------------------------
"""
__author__ = 'JHao'

import os
import setting
from util.singleton import Singleton
from util.lazyProperty import LazyProperty
from util.six import reload_six, withMetaclass


class ConfigHandler(withMetaclass(Singleton)):

    def __init__(self):
        pass

    @LazyProperty
    def serverHost(self):
        return os.environ.get("HOST", setting.HOST)

    @LazyProperty
    def serverPort(self):
        return os.environ.get("PORT", setting.PORT)

    @LazyProperty
    def dbConn(self):
        return os.getenv("DB_CONN", setting.DB_CONN)

    @LazyProperty
    def tableName(self):
        return os.getenv("TABLE_NAME", setting.TABLE_NAME)

    @property
    def fetchers(self):
        reload_six(setting)
        return setting.PROXY_FETCHER

    @LazyProperty
    def httpUrl(self):
        return os.getenv("HTTP_URL", setting.HTTP_URL)

    @LazyProperty
    def httpsUrl(self):
        return os.getenv("HTTPS_URL", setting.HTTPS_URL)

    @LazyProperty
    def verifyTimeout(self):
        return int(os.getenv("VERIFY_TIMEOUT", setting.VERIFY_TIMEOUT))

    # @LazyProperty
    # def proxyCheckCount(self):
    #     return int(os.getenv("PROXY_CHECK_COUNT", setting.PROXY_CHECK_COUNT))

    @LazyProperty
    def maxFailCount(self):
        return int(os.getenv("MAX_FAIL_COUNT", setting.MAX_FAIL_COUNT))

    # @LazyProperty
    # def maxFailRate(self):
    #     return int(os.getenv("MAX_FAIL_RATE", setting.MAX_FAIL_RATE))

    @LazyProperty
    def poolSizeMin(self):
        return int(os.getenv("POOL_SIZE_MIN", setting.POOL_SIZE_MIN))

    @LazyProperty
    def proxyRegion(self):
        return bool(os.getenv("PROXY_REGION", setting.PROXY_REGION))

    @LazyProperty
    def timezone(self):
        return os.getenv("TIMEZONE", setting.TIMEZONE)

    @LazyProperty
    def aiApiKey(self):
        return os.getenv("AI_API_KEY", setting.AI_API_KEY)

    @LazyProperty
    def aiApiBaseUrl(self):
        return os.getenv("AI_API_BASE_URL", setting.AI_API_BASE_URL)

    @LazyProperty
    def aiModel(self):
        return os.getenv("AI_MODEL", setting.AI_MODEL)

    @LazyProperty
    def aiSearchEnabled(self):
        env_val = os.getenv("AI_SEARCH_ENABLED")
        if env_val is not None:
            return env_val.lower() in ("1", "true", "yes")
        return bool(self.aiApiKey)

    @LazyProperty
    def aiSearchHour(self):
        return int(os.getenv("AI_SEARCH_HOUR", setting.AI_SEARCH_HOUR))

    @LazyProperty
    def aiMaxSources(self):
        return int(os.getenv("AI_MAX_SOURCES", setting.AI_MAX_SOURCES))

    @LazyProperty
    def aiApiTimeout(self):
        return int(os.getenv("AI_API_TIMEOUT", setting.AI_API_TIMEOUT))

