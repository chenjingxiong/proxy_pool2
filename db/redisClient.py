# -*- coding: utf-8 -*-
"""
-----------------------------------------------------
   File Name：     redisClient.py
   Description :   封装Redis相关操作
   Author :        JHao
   date：          2019/8/9
------------------------------------------------------
   Change Activity:
                   2019/08/09: 封装Redis相关操作
                   2020/06/23: 优化pop方法, 改用hscan命令
                   2021/05/26: 区别http/https代理
                   2026/06/16: 加权选取替代随机选取（鲜活度+速度）
------------------------------------------------------
"""
__author__ = 'JHao'

import os
import time as _time
import math
import json
from datetime import datetime
from redis.exceptions import TimeoutError, ConnectionError, ResponseError
from redis.connection import BlockingConnectionPool
from handler.logHandler import LogHandler
from random import choices as _choices, choice
from redis import Redis

# 加权选取权重（可通过环境变量覆盖）
_W_RECENCY = float(os.getenv("PROXY_WEIGHT_RECENCY", "0.7"))
_W_SPEED = float(os.getenv("PROXY_WEIGHT_SPEED", "0.3"))


def _proxy_score(data, now):
    """根据鲜活度和速度计算代理得分，得分越高越优先被选中"""
    lt = data.get("last_time", "")
    try:
        ts = datetime.strptime(lt, "%Y-%m-%d %H:%M:%S").timestamp() if lt else 0
    except Exception:
        ts = 0
    age = max(1.0, now - ts) if ts > 0 else 1e9
    # 指数衰减：刚验证=1.0, 1分钟前≈0.37, 5分钟前≈0.01
    recency = math.exp(-age / 60.0)
    # 速度得分：越快越高，归一化到 [0, 1]
    speed = max(0.05, float(data.get("speed") or 1.0))
    speed_score = min(1.0, 1.0 / speed / 5.0)
    return _W_RECENCY * recency + _W_SPEED * speed_score


def _safe_get(json_str, key, default=None):
    """安全从 JSON 字符串中取值"""
    try:
        return json.loads(json_str).get(key, default)
    except Exception:
        return default


class RedisClient(object):
    """
    Redis client

    Redis中代理存放的结构为hash：
    key为ip:port, value为代理属性的字典;

    """

    def __init__(self, **kwargs):
        """
        init
        :param host: host
        :param port: port
        :param password: password
        :param db: db
        :return:
        """
        self.name = ""
        kwargs.pop("username", None)
        self.__conn = Redis(connection_pool=BlockingConnectionPool(decode_responses=True,
                                                                   timeout=5,
                                                                   socket_timeout=5,
                                                                   **kwargs))

    def get(self, https, scheme=None):
        """
        加权选取一个代理：鲜活度+速度加权，优先返回最近验证通过且速度快的代理。
        从 last_status=True 或 last_status=None（加密协议待激活）的代理中选取。
        scheme 参数可指定只选取某种协议（http/https/socks5/vmess/vless/trojan/ss）。
        """
        items = self.__conn.hvals(self.name)
        if not items:
            return None
        if https:
            items = [x for x in items if _safe_get(x, "https")]
        if scheme:
            items = [x for x in items if _safe_get(x, "scheme", "http") == scheme]
        # 仅选取 last_status != False 的代理（True 或 None）
        valid = []
        for item in items:
            try:
                d = json.loads(item)
                ls = d.get("last_status")
                if ls is False:
                    continue
                valid.append((item, d))
            except Exception:
                pass
        if not valid:
            # 全部验证失败时 fallback 到任意代理
            return choice(items) if items else None
        if len(valid) == 1:
            return valid[0][0]
        now = _time.time()
        scores = [max(0.001, _proxy_score(d, now)) for _, d in valid]
        items_only = [v[0] for v in valid]
        return _choices(items_only, weights=scores, k=1)[0]

    def put(self, proxy_obj):
        """
        将代理放入hash, 使用changeTable指定hash name
        :param proxy_obj: Proxy obj
        :return:
        """
        data = self.__conn.hset(self.name, proxy_obj.proxy, proxy_obj.to_json)
        return data

    def pop(self, https):
        """
        弹出一个代理
        :return: dict {proxy: value}
        """
        proxy = self.get(https)
        if proxy:
            self.__conn.hdel(self.name, json.loads(proxy).get("proxy", ""))
        return proxy if proxy else None

    def delete(self, proxy_str):
        """
        移除指定代理, 使用changeTable指定hash name
        :param proxy_str: proxy str
        :return:
        """
        return self.__conn.hdel(self.name, proxy_str)

    def exists(self, proxy_str):
        """
        判断指定代理是否存在, 使用changeTable指定hash name
        :param proxy_str: proxy str
        :return:
        """
        return self.__conn.hexists(self.name, proxy_str)

    def update(self, proxy_obj):
        """
        更新 proxy 属性
        :param proxy_obj:
        :return:
        """
        return self.__conn.hset(self.name, proxy_obj.proxy, proxy_obj.to_json)

    def getAll(self, https):
        """
        字典形式返回所有代理, 使用changeTable指定hash name
        :return:
        """
        items = self.__conn.hvals(self.name)
        if https:
            return list(filter(lambda x: json.loads(x).get("https"), items))
        else:
            return items

    def clear(self):
        """
        清空所有代理, 使用changeTable指定hash name
        :return:
        """
        return self.__conn.delete(self.name)

    def getCount(self):
        """
        返回代理数量
        :return:
        """
        proxies = self.getAll(https=False)
        return {'total': len(proxies), 'https': len(list(filter(lambda x: json.loads(x).get("https"), proxies)))}

    def changeTable(self, name):
        """
        切换操作对象
        :param name:
        :return:
        """
        self.name = name

    def test(self):
        log = LogHandler('redis_client')
        try:
            self.getCount()
        except TimeoutError as e:
            log.error('redis connection time out: %s' % str(e), exc_info=True)
            return e
        except ConnectionError as e:
            log.error('redis connection error: %s' % str(e), exc_info=True)
            return e
        except ResponseError as e:
            log.error('redis connection error: %s' % str(e), exc_info=True)
            return e


