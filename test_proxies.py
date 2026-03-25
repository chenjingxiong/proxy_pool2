#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Proxy Pool Testing Script
Fetches proxies from various sources and tests them
"""
import sys
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from fetcher.proxyFetcher import ProxyFetcher

# Test URLs
TEST_HTTP_URL = "http://httpbin.org/ip"
TEST_HTTPS_URL = "https://api.ipify.org?format=json"
TIMEOUT = 10

# Results storage
results = {
    "fetched": [],
    "tested": [],
    "working_http": [],
    "working_https": [],
    "failed": [],
    "errors": []
}


def fetch_all_proxies():
    """Fetch proxies from all sources"""
    print("=" * 60)
    print("Fetching proxies from all sources...")
    print("=" * 60)

    fetcher = ProxyFetcher()
    methods = [m for m in dir(fetcher) if m.startswith('freeProxy')]

    all_proxies = set()

    for method_name in methods:
        print(f"\n[*] Fetching from {method_name}...")
        try:
            method = getattr(fetcher, method_name)
            count = 0
            for proxy in method():
                all_proxies.add(proxy)
                count += 1
            print(f"    -> Fetched {count} proxies from {method_name}")
        except Exception as e:
            print(f"    -> Error fetching from {method_name}: {e}")
            results["errors"].append(f"Fetch {method_name}: {str(e)}")

    results["fetched"] = list(all_proxies)
    print(f"\n[*] Total unique proxies fetched: {len(all_proxies)}")
    return all_proxies


def test_proxy(proxy, test_https=False):
    """Test a single proxy"""
    proxies = {
        'http': f'http://{proxy}',
        'https': f'http://{proxy}'
    }

    # Test HTTP
    try:
        start = time.time()
        response = requests.get(TEST_HTTP_URL, proxies=proxies, timeout=TIMEOUT)
        elapsed = time.time() - start
        if response.status_code == 200:
            data = response.json()
            return {
                'proxy': proxy,
                'http': True,
                'https': None,
                'response_time': round(elapsed, 2),
                'ip': data.get('origin', 'unknown')
            }
    except Exception as e:
        pass

    # Test HTTPS if requested
    if test_https:
        try:
            start = time.time()
            response = requests.get(TEST_HTTPS_URL, proxies=proxies, timeout=TIMEOUT)
            elapsed = time.time() - start
            if response.status_code == 200:
                return {
                    'proxy': proxy,
                    'http': False,
                    'https': True,
                    'response_time': round(elapsed, 2),
                    'ip': response.json().get('ip', 'unknown')
                }
        except Exception as e:
            pass

    return {
        'proxy': proxy,
        'http': False,
        'https': False,
        'response_time': None,
        'error': 'Failed'
    }


def test_proxies_parallel(proxies, max_workers=50):
    """Test multiple proxies in parallel"""
    print(f"\n[*] Testing {len(proxies)} proxies (parallel, {max_workers} workers)...")
    print("=" * 60)

    working = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(test_proxy, proxy): proxy for proxy in proxies}

        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            results["tested"].append(result)

            if result.get('http') or result.get('https'):
                working.append(result)
                if result.get('http'):
                    results["working_http"].append(result)
                if result.get('https'):
                    results["working_https"].append(result)
                print(f"[{i}/{len(proxies)}] ✓ {result['proxy']} - HTTP: {result['http']}, HTTPS: {result.get('https', False)}, Time: {result['response_time']}s, IP: {result.get('ip', 'N/A')}")
            else:
                results["failed"].append(result)
                if i % 10 == 0:
                    print(f"[{i}/{len(proxies)}] ... tested {i} proxies, {len(working)} working so far")

    return working


def print_report():
    """Print test report"""
    print("\n" + "=" * 60)
    print("PROXY POOL TEST REPORT")
    print("=" * 60)
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\n--- Summary ---")
    print(f"Total Proxies Fetched: {len(results['fetched'])}")
    print(f"Total Proxies Tested: {len(results['tested'])}")
    print(f"Working HTTP Proxies: {len(results['working_http'])}")
    print(f"Working HTTPS Proxies: {len(results['working_https'])}")
    print(f"Failed Proxies: {len(results['failed'])}")

    if results['working_http']:
        print(f"\n--- Top 10 Fastest HTTP Proxies ---")
        sorted_http = sorted(results['working_http'], key=lambda x: x['response_time'])[:10]
        for r in sorted_http:
            print(f"  {r['proxy']:20s} - {r['response_time']}s - IP: {r.get('ip', 'N/A')}")

    if results['working_https']:
        print(f"\n--- Top 10 Fastest HTTPS Proxies ---")
        sorted_https = sorted(results['working_https'], key=lambda x: x['response_time'])[:10]
        for r in sorted_https:
            print(f"  {r['proxy']:20s} - {r['response_time']}s - IP: {r.get('ip', 'N/A')}")

    if results['errors']:
        print(f"\n--- Errors ---")
        for e in results['errors'][:5]:
            print(f"  {e}")

    # Save to file
    with open('/tmp/proxy_test_report.txt', 'w') as f:
        f.write("=" * 60 + "\n")
        f.write("PROXY POOL TEST REPORT\n")
        f.write("=" * 60 + "\n")
        f.write(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"\n--- Summary ---\n")
        f.write(f"Total Proxies Fetched: {len(results['fetched'])}\n")
        f.write(f"Total Proxies Tested: {len(results['tested'])}\n")
        f.write(f"Working HTTP Proxies: {len(results['working_http'])}\n")
        f.write(f"Working HTTPS Proxies: {len(results['working_https'])}\n")
        f.write(f"Failed Proxies: {len(results['failed'])}\n")
        f.write(f"Success Rate: {len(results['working_http']) / len(results['tested']) * 100:.2f}%\n" if results['tested'] else "N/A\n")

        f.write(f"\n--- All Working HTTP Proxies ({len(results['working_http'])}) ---\n")
        for r in results['working_http']:
            f.write(f"{r['proxy']} - {r['response_time']}s - IP: {r.get('ip', 'N/A')}\n")

        f.write(f"\n--- All Working HTTPS Proxies ({len(results['working_https'])}) ---\n")
        for r in results['working_https']:
            f.write(f"{r['proxy']} - {r['response_time']}s - IP: {r.get('ip', 'N/A')}\n")

    print(f"\n--- Report saved to /tmp/proxy_test_report.txt ---")


def main():
    proxies = fetch_all_proxies()

    if not proxies:
        print("[!] No proxies fetched!")
        return

    test_proxies_parallel(proxies)
    print_report()


if __name__ == '__main__':
    main()
