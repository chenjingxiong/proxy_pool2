# -*- coding: utf-8 -*-
"""
测试代理池中所有代理的可用性，输出详细报告，并删除不可用的代理。
"""
import json
import time
import socket
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from redis import Redis

REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6380
REDIS_PASSWORD = "pwd"
REDIS_DB = 0
TABLE_NAME = "use_proxy"

# 验证目标 - 使用多个站点确保测试准确性
TEST_URLS = {
    "http_bin_ip": "https://httpbin.org/ip",
    "baidu": "https://www.baidu.com",
    "http_test": "http://httpbin.org/ip",
}

TIMEOUT = 8
MAX_WORKERS = 50


def get_all_proxies():
    """从 Redis 获取所有代理"""
    conn = Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD,
                 db=REDIS_DB, decode_responses=True)
    items = conn.hgetall(TABLE_NAME)
    proxies = []
    for key, val in items.items():
        try:
            data = json.loads(val)
            data["key"] = key
            proxies.append(data)
        except json.JSONDecodeError:
            proxies.append({"key": key, "proxy": key, "https": False})
    return proxies, conn


def test_single_proxy(proxy_data):
    """测试单个代理的可用性"""
    proxy_str = proxy_data.get("proxy", proxy_data["key"])
    results = {}
    success_count = 0
    fastest_speed = float("inf")

    for name, url in TEST_URLS.items():
        scheme = "https" if url.startswith("https") else "http"
        proxies = {
            "http": f"http://{proxy_str}",
            "https": f"http://{proxy_str}",
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        try:
            start = time.time()
            resp = requests.get(url, headers=headers, proxies=proxies,
                                timeout=TIMEOUT, verify=False, allow_redirects=True)
            elapsed = time.time() - start
            if resp.status_code == 200:
                results[name] = {"status": "OK", "code": resp.status_code,
                                 "time": round(elapsed, 2)}
                success_count += 1
                fastest_speed = min(fastest_speed, elapsed)
            else:
                results[name] = {"status": "FAIL", "code": resp.status_code,
                                 "time": round(elapsed, 2)}
        except requests.exceptions.ProxyError:
            results[name] = {"status": "PROXY_ERROR", "code": None, "time": None}
        except requests.exceptions.ConnectTimeout:
            results[name] = {"status": "TIMEOUT", "code": None, "time": None}
        except requests.exceptions.ReadTimeout:
            results[name] = {"status": "READ_TIMEOUT", "code": None, "time": None}
        except requests.exceptions.ConnectionError:
            results[name] = {"status": "CONN_ERROR", "code": None, "time": None}
        except Exception as e:
            results[name] = {"status": f"ERROR({type(e).__name__})", "code": None, "time": None}

    is_usable = success_count > 0
    speed = round(fastest_speed, 2) if fastest_speed != float("inf") else None

    return {
        "proxy": proxy_str,
        "https": proxy_data.get("https", False),
        "source": proxy_data.get("source", "unknown"),
        "usable": is_usable,
        "success_count": success_count,
        "total_tests": len(TEST_URLS),
        "speed": speed,
        "details": results,
    }


def delete_bad_proxies(conn, bad_proxies):
    """从 Redis 中删除不可用的代理"""
    if not bad_proxies:
        return 0
    pipe = conn.pipeline()
    for p in bad_proxies:
        pipe.hdel(TABLE_NAME, p)
    pipe.execute()
    return len(bad_proxies)


def generate_report(results, deleted_count, elapsed):
    """生成详细报告"""
    total = len(results)
    usable = [r for r in results if r["usable"]]
    unusable = [r for r in results if not r["usable"]]
    http_only = [r for r in usable if not r["https"]]
    https_capable = [r for r in usable if r["https"]]

    # 按速度排序
    speed_ranked = sorted([r for r in usable if r["speed"]], key=lambda x: x["speed"])

    # 统计失败原因
    fail_reasons = {}
    for r in unusable:
        for name, detail in r["details"].items():
            reason = detail["status"]
            fail_reasons[reason] = fail_reasons.get(reason, 0) + 1

    # 来源统计
    source_stats = {}
    for r in results:
        src = r.get("source", "unknown")
        if src not in source_stats:
            source_stats[src] = {"total": 0, "usable": 0}
        source_stats[src]["total"] += 1
        if r["usable"]:
            source_stats[src]["usable"] += 1

    # 速度分布
    speeds = [r["speed"] for r in usable if r["speed"]]
    avg_speed = round(sum(speeds) / len(speeds), 2) if speeds else 0

    sep = "=" * 70
    lines = []
    lines.append(sep)
    lines.append("            代理池可用性测试报告")
    lines.append(sep)
    lines.append(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"测试耗时: {round(elapsed, 1)} 秒")
    lines.append(f"并发数:   {MAX_WORKERS}")
    lines.append(f"验证目标: {', '.join(TEST_URLS.keys())}")
    lines.append("")
    lines.append(sep)
    lines.append("一、总体概况")
    lines.append(sep)
    lines.append(f"  总代理数:        {total}")
    lines.append(f"  可用代理数:      {len(usable)}  ({round(len(usable)/total*100, 1)}%)")
    lines.append(f"  不可用代理数:    {len(unusable)}  ({round(len(unusable)/total*100, 1)}%)")
    lines.append(f"  已删除不可用:    {deleted_count}")
    lines.append("")
    https_pct = round(len(https_capable)/max(len(usable),1)*100, 1)
    lines.append(f"  支持 HTTPS:     {len(https_capable)}  ({https_pct}%)")
    lines.append(f"  仅 HTTP:        {len(http_only)}")
    lines.append("")
    lines.append(sep)
    lines.append("二、速度统计 (可用代理)")
    lines.append(sep)
    lines.append(f"  平均响应速度:    {avg_speed} 秒")
    if speed_ranked:
        lines.append(f"  最快速度:        {speed_ranked[0]['speed']} 秒  ({speed_ranked[0]['proxy']})")
    else:
        lines.append("  最快速度:        N/A")
    if len(speed_ranked) >= 2:
        lines.append(f"  最慢速度:        {speed_ranked[-1]['speed']} 秒  ({speed_ranked[-1]['proxy']})")
    lines.append("")
    lines.append(sep)
    lines.append("三、速度 Top 10 (最快)")
    lines.append(sep)
    for i, r in enumerate(speed_ranked[:10], 1):
        lines.append(f"  {i:2d}. {r['proxy']:25s}  {r['speed']:5.2f}s  (通过 {r['success_count']}/{r['total_tests']} 测试)")
    lines.append("")
    lines.append(sep)
    lines.append("四、失败原因统计")
    lines.append(sep)
    for reason, count in sorted(fail_reasons.items(), key=lambda x: -x[1]):
        lines.append(f"  {reason:20s}: {count:4d}  ({round(count/len(unusable)*100, 1)}%)")
    lines.append("")
    lines.append(sep)
    lines.append("五、来源可用性统计")
    lines.append(sep)
    sorted_sources = sorted(source_stats.items(), key=lambda x: -x[1]["usable"])
    for src, stat in sorted_sources[:20]:
        rate = round(stat["usable"] / stat["total"] * 100, 1)
        bar = "#" * int(rate / 5) + "-" * (20 - int(rate / 5))
        lines.append(f"  {src[:40]:40s}  {stat['usable']:3d}/{stat['total']:3d}  [{bar}] {rate:5.1f}%")
    if len(sorted_sources) > 20:
        lines.append(f"  ... 还有 {len(sorted_sources)-20} 个来源未显示")
    lines.append("")
    lines.append(sep)
    lines.append(f"六、所有可用代理列表 ({len(usable)} 个)")
    lines.append(sep)
    for i, r in enumerate(speed_ranked, 1):
        https_mark = "HTTPS" if r["https"] else "HTTP "
        speed_str = f"{r['speed']:.2f}" if r["speed"] else "N/A"
        lines.append(f"  {i:3d}. [{https_mark}] {r['proxy']:25s}  {speed_str:>6s}s  来源:{r.get('source','?')}")
    lines.append("")
    lines.append(sep)
    return "\n".join(lines)


if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    print("正在从 Redis 加载代理...")
    proxies_list, conn = get_all_proxies()
    print(f"共加载 {len(proxies_list)} 个代理，开始测试...\n")

    results = []
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(test_single_proxy, p): p for p in proxies_list}
        done_count = 0
        for future in as_completed(futures):
            done_count += 1
            result = future.result()
            status = "OK" if result["usable"] else "FAIL"
            if done_count % 50 == 0 or done_count == len(proxies_list):
                print(f"  进度: {done_count}/{len(proxies_list)} "
                      f"(可用: {sum(1 for r in results if r['usable'])})")
            results.append(result)

    elapsed = time.time() - start_time

    # 删除不可用的代理
    bad_keys = [r["proxy"] for r in results if not r["usable"]]
    print(f"\n正在删除 {len(bad_keys)} 个不可用代理...")
    deleted = delete_bad_proxies(conn, bad_keys)
    print(f"已删除 {deleted} 个不可用代理。\n")

    # 生成报告
    report = generate_report(results, deleted, elapsed)
    print(report)

    # 保存报告到文件
    with open("/root/projects/proxy_pool/PROXY_TEST_REPORT.md", "w") as f:
        f.write(report)
    print("报告已保存到 PROXY_TEST_REPORT.md")
