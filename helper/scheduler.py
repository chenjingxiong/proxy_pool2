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
from helper.proxy import SCHEMES_ENCRYPTED


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


def __runMihomoSync():
    """把池中的加密协议节点同步到 mihomo 配置，并测试延迟"""
    conf = ConfigHandler()
    if not conf.mihomoEnabled:
        return
    from handler.mihomoHandler import MihomoClient
    client = MihomoClient()

    # 检查 mihomo 是否在线
    if not client.is_available():
        LogHandler("mihomo_sync").info("mihomo not available, skipping sync")
        return

    ph = ProxyHandler()
    encrypted_proxies = [p for p in ph.getAll() if p.scheme in SCHEMES_ENCRYPTED]

    if not encrypted_proxies:
        return

    # 生成并热加载配置
    yaml_str = client.generate_config_yaml(encrypted_proxies)
    if not client.reload_config(yaml_str):
        LogHandler("mihomo_sync").warning("mihomo config reload failed")
        return

    LogHandler("mihomo_sync").info(
        "mihomo synced %d encrypted proxies", len(encrypted_proxies)
    )

    # 延迟测试并回写 speed + last_status
    for proxy in encrypted_proxies:
        if not proxy.raw_uri:
            continue
        # 从 raw_uri 提取 Clash 条目 name 用于测试
        from handler.mihomoHandler import _uri_to_clash_entry
        entry = _uri_to_clash_entry(proxy.raw_uri, proxy.scheme)
        if not entry:
            continue
        name = entry.get("name", "")
        if not name:
            continue
        delay = client.test_proxy(name)
        if delay > 0:
            proxy.speed = round(delay / 1000.0, 3)  # ms → s
            proxy.last_status = True
            proxy.last_time = __now_str()
        else:
            proxy.last_status = False
            proxy.last_time = __now_str()
        proxy.check_count = (proxy.check_count or 0) + 1
        ph.put(proxy)


def __now_str():
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


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

    if conf.mihomoEnabled:
        scheduler.add_job(__runMihomoSync, 'interval', minutes=conf.mihomoSyncIntervalMin,
                          id="mihomo_sync", name="mihomo配置同步",
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
