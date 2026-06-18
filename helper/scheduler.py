# -*- coding: utf-8 -*-
"""
-------------------------------------------------
   File Name：     proxyScheduler
   Description :
   Author :        JHao
   date：          2019/8/5
-------------------------------------------------
   Change Activity:
                   2019/08/05: proxyScheduler
                   2021/02/23: runProxyCheck时,剩余代理少于POOL_SIZE_MIN时执行抓取
-------------------------------------------------
"""
__author__ = 'JHao'

from apscheduler.schedulers.blocking import BlockingScheduler

from util.six import Queue
from helper.fetch import Fetcher
from helper.check import Checker
from handler.logHandler import LogHandler
from handler.proxyHandler import ProxyHandler
from handler.configHandler import ConfigHandler
from handler.refreshHandler import runRefreshJob


def __runProxyFetch():
    proxy_queue = Queue()
    proxy_fetcher = Fetcher()

    for proxy in proxy_fetcher.run():
        proxy_queue.put(proxy)

    Checker("raw", proxy_queue)


def __runProxyCheck():
    proxy_handler = ProxyHandler()
    proxy_queue = Queue()
    if proxy_handler.db.getCount().get("total", 0) < proxy_handler.conf.poolSizeMin:
        __runProxyFetch()
    for proxy in proxy_handler.getAll():
        proxy_queue.put(proxy)
    Checker("use", proxy_queue)


def __runAISearch():
    """AI智能代理搜索"""
    conf = ConfigHandler()
    if not conf.aiSearchEnabled:
        return
    from fetcher.proxyFetcher import ProxyFetcher
    from helper.proxy import Proxy
    proxy_queue = Queue()
    for proxy_str in ProxyFetcher.aiProxySearch():
        proxy_queue.put(Proxy(proxy_str, source="aiProxySearch"))
    if not proxy_queue.empty():
        Checker("raw", proxy_queue)
        LogHandler("ai_search").info(
            f"AI search: validated {proxy_queue.qsize()} proxies"
        )


def runScheduler():
    __runProxyFetch()

    conf = ConfigHandler()
    timezone = conf.timezone
    scheduler_log = LogHandler("scheduler")
    scheduler = BlockingScheduler(logger=scheduler_log, timezone=timezone)

    # coalesce=True + max_instances=1：避免长任务与下一轮 fetch 重叠，导致 queue 堆积与内存膨胀
    scheduler.add_job(__runProxyFetch, 'interval', minutes=4,
                      id="proxy_fetch", name="proxy采集",
                      max_instances=1, coalesce=True)
    scheduler.add_job(__runProxyCheck, 'interval', minutes=conf.refreshIntervalMin,
                      id="proxy_check", name="proxy检查",
                      max_instances=1, coalesce=True)
    scheduler.add_job(runRefreshJob, 'interval', minutes=5,
                      id="proxy_refresh", name="proxy刷新",
                      max_instances=1, coalesce=True)

    if conf.aiSearchEnabled:
        scheduler.add_job(__runAISearch, 'cron', hour=conf.aiSearchHour, minute=0,
                          id="ai_proxy_search", name="AI代理搜索",
                          max_instances=1, coalesce=True)

    # 单一线程池足以串行/小并发执行上述任务；移除 ProcessPoolExecutor，避免额外 fork 进程
    executors = {
        'default': {'type': 'threadpool', 'max_workers': 4}
    }
    job_defaults = {
        'coalesce': True,
        'max_instances': 1
    }

    scheduler.configure(executors=executors, job_defaults=job_defaults, timezone=timezone)

    scheduler.start()


if __name__ == '__main__':
    runScheduler()
