#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Comprehensive Proxy Pool Testing Script
Tests all proxy sources and generates detailed report
"""
import sys
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from fetcher.proxyFetcher import ProxyFetcher

# Test URLs
TEST_HTTP_URL = "http://httpbin.org/ip"
TIMEOUT = 10

# Source descriptions
SOURCE_NAMES = {
    "freeProxy01": "站大爷 (zdaye.com)",
    "freeProxy02": "66代理 (66ip.cn)",
    "freeProxy03": "开心代理",
    "freeProxy04": "FreeProxyList",
    "freeProxy05": "快代理 (kuaidaili.com)",
    "freeProxy06": "冰凌代理 (binglx.cn)",
    "freeProxy07": "云代理 (ip3366.net)",
    "freeProxy08": "小幻代理",
    "freeProxy09": "免费代理库",
    "freeProxy10": "89代理 (89ip.cn)",
    "freeProxy11": "稻壳代理 (docip.net)",
    "freeProxyScdn": "SCDN代理池 (proxy.scdn.io)",
    "freeProxy12": "Proxifly GitHub (HTTP)",
    "freeProxy13": "JetKai GitHub (HTTP)",
    "freeProxy14": "ProxyScrape API (HTTP)",
    "freeProxy15": "Seladb GitHub (HTTP)",
    "freeProxy16": "TheSpeedX PROXIER",
    "freeProxy17": "Monosans GitHub (HTTP)",
    "freeProxy18": "ClarkeTM GitHub",
    "freeProxy19": "GfpCom GitHub (HTTP)",
    "freeProxy20": "Fate0 GitHub",
    "freeProxy21": "TopChina GitHub (HTTP)",
    "freeProxy22": "Databay Labs GitHub (HTTP)",
    "freeProxy23": "Casa-LS GitHub (HTTP)",
    "freeProxy24": "Iplocate GitHub (HTTP)",
    "freeProxy25": "LeChann GitHub (HTTP)",
    "freeProxy26": "Rdavydov GitHub (HTTP)",
    "freeProxy27": "Mertguvencli GitHub",
    "freeProxy28": "Zaeem20 GitHub (HTTP)",
    "freeProxy29": "R00tee GitHub (HTTP)",
    "freeProxy30": "MrMarble GitHub (HTTPS)",
    "freeProxy31": "Fyvri GitHub (HTTP)",
    "freeProxy32": "Anonym0usWork1221 (HTTP)",
    "freeProxy33": "ProbiusOfficial GitHub (HTTP)",
    "freeProxy34": "V2era GitHub (HTTP)",
    "freeProxy35": "S4wfit GitHub (HTTP)",
    "freeProxy36": "Watchttvv GitHub",
    "freeProxy37": "Roosterkid GitHub",
    "freeProxy38": "Shjalayeri GitHub",
    "freeProxy39": "ALIILAPRO GitHub",
    "freeProxy40": "Officialpiyush GitHub (HTTPS)",
    "freeProxy41": "Abovlms GitHub",
    "freeProxy42": "Hidesslayer GitHub (HTTP)",
    "freeProxy43": "Zevtyardt GitHub (HTTP)",
    "freeProxy44": "Ethereum-ex GitHub (HTTP)",
    "freeProxy45": "Wklchris GitHub",
    "freeProxy46": "Mmpx12 GitHub",
    "freeProxy47": "OpenProxyList API",
    "freeProxy48": "ProxyScrape API (SOCKS4)",
    "freeProxy49": "ProxyScrape API (SOCKS5)",
    "freeProxy50": "Proxifly GitHub (HTTPS)",
}

# Results storage
results = {
    "sources": {},
    "total_fetched": 0,
    "total_tested": 0,
    "total_working": 0,
    "all_working_proxies": []
}


def test_proxy(proxy):
    """Test a single proxy"""
    proxies = {'http': f'http://{proxy}'}
    try:
        start = time.time()
        response = requests.get(TEST_HTTP_URL, proxies=proxies, timeout=TIMEOUT)
        elapsed = time.time() - start
        if response.status_code == 200:
            data = response.json()
            return {
                'proxy': proxy,
                'working': True,
                'response_time': round(elapsed, 2),
                'ip': data.get('origin', 'unknown')
            }
    except Exception:
        pass
    return {'proxy': proxy, 'working': False, 'response_time': None}


def test_source(source_name, source_method):
    """Test a single proxy source"""
    print(f"\n[*] Testing {source_name}: {SOURCE_NAMES.get(source_name, 'Unknown')}")
    print("-" * 60)

    source_result = {
        "name": SOURCE_NAMES.get(source_name, source_name),
        "fetched": 0,
        "tested": 0,
        "working": 0,
        "proxies": []
    }

    try:
        # Fetch proxies
        proxies = list(source_method())
        source_result["fetched"] = len(proxies)

        if len(proxies) == 0:
            print(f"    -> No proxies fetched")
            results["sources"][source_name] = source_result
            return source_result

        print(f"    -> Fetched {len(proxies)} proxies")

        # Limit testing to first 50 proxies per source for speed
        proxies_to_test = proxies[:50] if len(proxies) > 50 else proxies

        # Test proxies
        working = []
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = {executor.submit(test_proxy, proxy): proxy for proxy in proxies_to_test}

            for future in as_completed(futures):
                result = future.result()
                source_result["tested"] += 1

                if result.get('working'):
                    working.append(result)
                    source_result["working"] += 1
                    results["all_working_proxies"].append(result)
                    print(f"    ✓ {result['proxy']} - {result['response_time']}s")

        source_result["proxies"] = working
        success_rate = (source_result["working"] / source_result["tested"] * 100) if source_result["tested"] > 0 else 0
        print(f"    -> {source_result['working']}/{source_result['tested']} working ({success_rate:.1f}%)")

    except Exception as e:
        print(f"    -> Error: {e}")
        source_result["error"] = str(e)

    results["sources"][source_name] = source_result
    results["total_fetched"] += source_result["fetched"]
    results["total_tested"] += source_result["tested"]
    results["total_working"] += source_result["working"]

    return source_result


def print_report():
    """Print comprehensive test report"""
    print("\n" + "=" * 80)
    print(" " * 20 + "COMPREHENSIVE PROXY POOL TEST REPORT")
    print("=" * 80)
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Sources Tested: {len(results['sources'])}")

    print("\n" + "-" * 80)
    print("SUMMARY")
    print("-" * 80)
    print(f"Total Proxies Fetched: {results['total_fetched']}")
    print(f"Total Proxies Tested: {results['total_tested']}")
    print(f"Total Working Proxies: {results['total_working']}")
    if results['total_tested'] > 0:
        print(f"Overall Success Rate: {results['total_working'] / results['total_tested'] * 100:.2f}%")

    print("\n" + "-" * 80)
    print("SOURCE RANKING (by working proxies)")
    print("-" * 80)
    print(f"{'Rank':<5} {'Source':<45} {'Fetched':<10} {'Tested':<10} {'Working':<10} {'Rate':<10}")
    print("-" * 80)

    sorted_sources = sorted(
        [(k, v) for k, v in results["sources"].items() if v.get("tested", 0) > 0],
        key=lambda x: x[1]["working"],
        reverse=True
    )

    for i, (name, data) in enumerate(sorted_sources, 1):
        rate = (data["working"] / data["tested"] * 100) if data["tested"] > 0 else 0
        print(f"{i:<5} {data['name'][:43]:<45} {data['fetched']:<10} {data['tested']:<10} {data['working']:<10} {rate:<10.1f}%")

    print("\n" + "-" * 80)
    print("FAILED SOURCES")
    print("-" * 80)
    failed_sources = [(k, v) for k, v in results["sources"].items() if v.get("tested", 0) == 0]
    if failed_sources:
        for name, data in failed_sources:
            print(f"  {data['name']}: {data.get('error', 'No proxies fetched')}")
    else:
        print("  All sources returned proxies!")

    print("\n" + "-" * 80)
    print("TOP 30 FASTEST WORKING PROXIES")
    print("-" * 80)

    sorted_proxies = sorted(results["all_working_proxies"], key=lambda x: x["response_time"])[:30]
    for i, p in enumerate(sorted_proxies, 1):
        print(f"  {i:2d}. {p['proxy']:25s} - {p['response_time']}s - IP: {p.get('ip', 'N/A')}")

    # Save detailed report
    with open('/tmp/comprehensive_proxy_test_report.txt', 'w') as f:
        f.write("=" * 80 + "\n")
        f.write(" " * 20 + "COMPREHENSIVE PROXY POOL TEST REPORT\n")
        f.write("=" * 80 + "\n")
        f.write(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Sources Tested: {len(results['sources'])}\n")

        f.write("\n" + "-" * 80 + "\n")
        f.write("SUMMARY\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total Proxies Fetched: {results['total_fetched']}\n")
        f.write(f"Total Proxies Tested: {results['total_tested']}\n")
        f.write(f"Total Working Proxies: {results['total_working']}\n")
        if results['total_tested'] > 0:
            f.write(f"Overall Success Rate: {results['total_working'] / results['total_tested'] * 100:.2f}%\n")

        f.write("\n" + "-" * 80 + "\n")
        f.write("DETAILED SOURCE RESULTS\n")
        f.write("-" * 80 + "\n")

        for name, data in results["sources"].items():
            f.write(f"\n{data['name']} ({name}):\n")
            f.write(f"  Fetched: {data['fetched']}\n")
            f.write(f"  Tested: {data['tested']}\n")
            f.write(f"  Working: {data['working']}\n")
            if data.get("error"):
                f.write(f"  Error: {data['error']}\n")
            if data.get("proxies"):
                f.write(f"  Working Proxies:\n")
                for p in data["proxies"][:10]:
                    f.write(f"    {p['proxy']} - {p['response_time']}s\n")

        f.write("\n" + "-" * 80 + "\n")
        f.write("ALL WORKING PROXIES\n")
        f.write("-" * 80 + "\n")
        sorted_proxies = sorted(results["all_working_proxies"], key=lambda x: x["response_time"])
        for p in sorted_proxies:
            f.write(f"{p['proxy']} - {p['response_time']}s - IP: {p.get('ip', 'N/A')}\n")

    print(f"\n--- Detailed report saved to /tmp/comprehensive_proxy_test_report.txt ---")


def main():
    print("=" * 80)
    print(" " * 25 + "PROXY POOL COMPREHENSIVE TEST")
    print("=" * 80)
    print("Testing 50+ proxy sources... This will take several minutes.")

    fetcher = ProxyFetcher()

    # Test all new sources (12-50)
    new_sources = []
    for i in range(12, 51):
        method_name = f"freeProxy{i:02d}" if i >= 12 else f"freeProxy{i}"
        if i == 12:
            method_name = "freeProxy12"
        elif hasattr(fetcher, method_name):
            new_sources.append(method_name)

    # Also test freeProxyScdn
    new_sources.append("freeProxyScdn")

    # Remove duplicates
    new_sources = list(set(new_sources))

    print(f"\nFound {len(new_sources)} sources to test")

    for source_name in new_sources:
        if hasattr(fetcher, source_name):
            method = getattr(fetcher, source_name)
            test_source(source_name, method)
        else:
            print(f"[!] Source {source_name} not found")

    print_report()


if __name__ == '__main__':
    main()
