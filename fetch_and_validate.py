# -*- coding: utf-8 -*-
"""
快速代理抓取策略：抽样验证 → 批量入库高质量源 → 全量验证 → 清理
"""
import re
import json
import time
import random
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from redis import Redis
from helper.proxy import Proxy

REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6380
REDIS_PASSWORD = "pwd"
REDIS_DB = 0
TABLE_NAME = "use_proxy"

TEST_URLS = [
    "https://httpbin.org/ip",
    "http://httpbin.org/ip",
    "https://www.baidu.com",
]
TIMEOUT = 8
FETCH_TIMEOUT = 25
MAX_WORKERS = 80

IP_REGEX = re.compile(r"(.*:.*@)?\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}")

# 代理源 URL 列表
TEXT_SOURCES = {
    "freeProxy12": "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/http/data.txt",
    "freeProxy13": "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt",
    "freeProxy15": "https://raw.githubusercontent.com/seladb/ProxyList/master/http.txt",
    "freeProxy17": "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "freeProxy18": "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
    "freeProxy43": "https://raw.githubusercontent.com/zevtyardt/proxy-list/main/http.txt",
    "freeProxy46": "https://raw.githubusercontent.com/mmpx12/Proxy-List/master/proxies.txt",
    "freeProxy47": "https://openproxylist.com/list.txt",
    "freeProxy50": "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/https/data.txt",
    "freeProxy51": "https://raw.githubusercontent.com/gitrecon1455/fresh-proxy-list/main/proxylist.txt",
    "freeProxy52": "https://raw.githubusercontent.com/SevenworksDev/proxy-list/main/proxies/http.txt",
    "freeProxy53": "https://raw.githubusercontent.com/mzyui/proxy-list/main/http.txt",
    "freeProxy54": "https://raw.githubusercontent.com/SevenworksDev/proxy-list/main/proxies/https.txt",
    "freeProxy55": "https://raw.githubusercontent.com/r00tee/Proxy-List/main/Https.txt",
    "freeProxy56": "https://raw.githubusercontent.com/Argh94/Proxy-List/main/HTTP.txt",
    "freeProxy57": "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=https&timeout=10000&country=all",
    "freeProxy60": "https://raw.githubusercontent.com/Vann-Dev/proxy-list/main/proxies/http.txt",
    "freeProxy62": "https://raw.githubusercontent.com/vakhov/fresh-proxy-list/master/http.txt",
    "freeProxy63": "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
    "freeProxy64": "https://raw.githubusercontent.com/MrMarble/proxy-list/main/all.txt",
    "freeProxy65": "https://raw.githubusercontent.com/databay-labs/free-proxy-list/master/http.txt",
    "freeProxy66": "https://raw.githubusercontent.com/themiralay/Proxy-List-World/master/data.txt",
    "freeProxy67": "https://raw.githubusercontent.com/Vann-Dev/proxy-list/main/proxies/https.txt",
    "freeProxy69": "https://raw.githubusercontent.com/prxchk/proxy-list/main/http.txt",
    "freeProxy71": "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS.txt",
    "freeProxy72": "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
    "freeProxy73": "https://raw.githubusercontent.com/watchttvv/free-proxy-list/main/proxy.txt",
    "freeProxy74": "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/https.txt",
    "freeProxy75": "https://raw.githubusercontent.com/vakhov/fresh-proxy-list/master/https.txt",
    "freeProxy76": "https://raw.githubusercontent.com/a2u/free-proxy-list/master/free-proxy-list.txt",
    "freeProxy77": "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "freeProxy82": "https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&protocol=all&timeout=10000&country=all",
    "freeProxy85": "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
    "freeProxy86": "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
    "freeProxy88": "https://raw.githubusercontent.com/rdavydov/Proxy-List/master/proxies/http.txt",
    "freeProxy90": "https://raw.githubusercontent.com/zevtyardt/proxy-list/main/socks4.txt",
    "freeProxy91": "https://raw.githubusercontent.com/zevtyardt/proxy-list/main/socks5.txt",
    "freeProxy96": "https://raw.githubusercontent.com/prxchk/proxy-list/main/socks5.txt",
    "freeProxy99": "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks5.txt",
    "freeProxyScdn": "https://proxy.scdn.io/text.php",
    "freeProxy87": "https://proxylist.geonode.com/api/proxy-list?protocols=http&limit=100&page=1&sort_by=lastChecked&sort_type=desc",
}

SCDN_API = "https://proxy.scdn.io/api/get_proxy.php?protocol=http&count=20"


def fetch_text_source(name, url):
    try:
        resp = requests.get(url, timeout=FETCH_TIMEOUT, verify=False,
                            headers={"User-Agent": "Mozilla/5.0"})
        proxies = []
        for line in resp.text.strip().split("\n"):
            line = line.strip()
            for prefix in ["socks4://", "socks5://", "http://", "https://"]:
                if line.startswith(prefix):
                    line = line[len(prefix):]
                    break
            if line and IP_REGEX.fullmatch(line):
                proxies.append(line)
        # scdn also has API
        if name == "freeProxyScdn":
            try:
                api_resp = requests.get(SCDN_API, timeout=FETCH_TIMEOUT, verify=False)
                api_data = api_resp.json()
                if api_data.get("code") == 200:
                    for p in api_data.get("data", {}).get("proxies", []):
                        if IP_REGEX.fullmatch(p) and p not in proxies:
                            proxies.append(p)
            except Exception:
                pass
        return name, proxies, None
    except Exception as e:
        return name, [], str(e)[:80]


def validate_proxy(proxy_str):
    for url in TEST_URLS:
        proxies = {"http": f"http://{proxy_str}", "https": f"http://{proxy_str}"}
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        try:
            start = time.time()
            resp = requests.get(url, headers=headers, proxies=proxies,
                                timeout=TIMEOUT, verify=False, allow_redirects=True)
            elapsed = time.time() - start
            if resp.status_code == 200:
                return proxy_str, True, round(elapsed, 2)
        except Exception:
            continue
    return proxy_str, False, None


def main():
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    conn = Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD,
                 db=REDIS_DB, decode_responses=True)

    existing = set(conn.hkeys(TABLE_NAME))
    print(f"当前池中已有 {len(existing)} 个代理")
    print(f"开始从 {len(TEXT_SOURCES)} 个代理源抓取新代理...\n")

    # ==================== 第一阶段：抓取 ====================
    fetch_start = time.time()
    all_proxies = {}  # proxy -> source
    source_stats = {}

    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = {executor.submit(fetch_text_source, n, u): n for n, u in TEXT_SOURCES.items()}
        for future in as_completed(futures):
            name, proxies, error = future.result()
            source_stats[name] = {"fetched": len(proxies), "error": error}
            # 每个源最多取 500 个（避免超大列表拖慢验证）
            sampled = proxies if len(proxies) <= 500 else random.sample(proxies, 500)
            for p in sampled:
                if p not in all_proxies:
                    all_proxies[p] = name
            status = f"获取 {len(proxies)} 个" if not error else f"失败: {error}"
            print(f"  [{name:20s}] {status}")

    new_proxies = {p: s for p, s in all_proxies.items() if p not in existing}
    fetch_elapsed = time.time() - fetch_start
    print(f"\n抓取完成！总抓取 {len(all_proxies)} 个，新增 {len(new_proxies)} 个，耗时 {round(fetch_elapsed, 1)}s")

    if not new_proxies:
        print("没有新代理。")
        return

    # ==================== 第二阶段：全量验证（并发80） ====================
    proxy_list = list(new_proxies.keys())
    print(f"\n开始验证 {len(proxy_list)} 个代理（并发 {MAX_WORKERS}）...\n")
    validate_start = time.time()
    usable = []
    unusable_count = 0
    done = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(validate_proxy, p): p for p in proxy_list}
        for future in as_completed(futures):
            proxy_str, is_usable, speed = future.result()
            done += 1
            if is_usable:
                usable.append((proxy_str, speed, new_proxies[proxy_str]))
            else:
                unusable_count += 1
            if done % 500 == 0 or done == len(proxy_list):
                pct = round(done / len(proxy_list) * 100, 1)
                print(f"  进度: {done}/{len(proxy_list)} ({pct}%) | 可用: {len(usable)}")

    validate_elapsed = time.time() - validate_start
    print(f"\n验证完成！可用 {len(usable)} 个，不可用 {unusable_count} 个，耗时 {round(validate_elapsed, 1)}s")

    # ==================== 第三阶段：写入 Redis ====================
    pipe = conn.pipeline()
    added = 0
    for proxy_str, speed, source in usable:
        proxy_obj = Proxy(proxy=proxy_str, source=source, speed=speed)
        pipe.hset(TABLE_NAME, proxy_str, proxy_obj.to_json)
        added += 1
    pipe.execute()

    final_count = conn.hlen(TABLE_NAME)

    # ==================== 报告 ====================
    sep = "=" * 60
    lines = [
        sep, "       代理抓取与验证报告", sep,
        f"抓取源数量:      {len(TEXT_SOURCES)}",
        f"抓取耗时:        {round(fetch_elapsed, 1)} 秒",
        f"验证耗时:        {round(validate_elapsed, 1)} 秒",
        f"总耗时:          {round(fetch_elapsed + validate_elapsed, 1)} 秒", "",
        f"总抓取(去重):    {len(all_proxies)}",
        f"新增代理:        {len(new_proxies)}",
        f"验证可用:        {len(usable)} ({round(len(usable)/max(len(new_proxies),1)*100,1)}%)",
        f"验证不可用:      {unusable_count}",
        f"新入库:          {added}",
        f"原有代理:        {len(existing)}",
        f"当前池总数:      {final_count}", "",
        sep, "抓取源统计 (按数量 Top 20):", sep,
    ]
    sorted_src = sorted(source_stats.items(), key=lambda x: -x[1]["fetched"])[:20]
    for name, stat in sorted_src:
        err = f" (错误: {stat['error']})" if stat["error"] else ""
        lines.append(f"  {name:20s}  获取: {stat['fetched']:5d}{err}")

    failed = [n for n, s in source_stats.items() if s["error"]]
    if failed:
        lines.append(f"\n失败源 ({len(failed)} 个):")
        for n in failed:
            lines.append(f"  - {n}: {source_stats[n]['error']}")

    if usable:
        speed_sorted = sorted(usable, key=lambda x: x[1])
        lines.extend(["", sep, "新入库可用代理 Top 20 (按速度):", sep])
        for i, (p, s, src) in enumerate(speed_sorted[:20], 1):
            lines.append(f"  {i:3d}. {p:25s}  {s:.2f}s  来源:{src}")

    lines.append(f"\n{sep}")
    report = "\n".join(lines)
    print(f"\n{report}")

    with open("/root/projects/proxy_pool/FETCH_REPORT.md", "w") as f:
        f.write(report)
    print("报告已保存到 FETCH_REPORT.md")


if __name__ == "__main__":
    main()
