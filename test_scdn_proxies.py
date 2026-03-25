#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SCDN Proxy Pool Testing Script
Tests proxies from https://proxy.scdn.io/
"""
import sys
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

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


def fetch_scdn_proxies():
    """Fetch proxies from SCDN"""
    print("=" * 60)
    print("Fetching proxies from SCDN (https://proxy.scdn.io/)")
    print("=" * 60)

    all_proxies = set()

    # Method 1: API
    print("\n[*] Fetching from API...")
    try:
        api_url = "https://proxy.scdn.io/api/get_proxy.php?protocol=http&count=20"
        resp = requests.get(api_url, timeout=15, verify=False)
        data = resp.json()
        if data.get('code') == 200:
            proxies = data.get('data', {}).get('proxies', [])
            for proxy in proxies:
                all_proxies.add(proxy)
            print(f"    -> Fetched {len(proxies)} proxies from API")
    except Exception as e:
        print(f"    -> Error fetching from API: {e}")
        results["errors"].append(f"API: {str(e)}")

    # Method 2: Text page
    print("\n[*] Fetching from Text page...")
    try:
        text_url = "https://proxy.scdn.io/text.php"
        resp = requests.get(text_url, timeout=30, verify=False)
        count = 0
        for line in resp.text.strip().split('\n'):
            line = line.strip()
            if line and ':' in line:
                all_proxies.add(line)
                count += 1
        print(f"    -> Fetched {count} proxies from Text page")
    except Exception as e:
        print(f"    -> Error fetching from Text page: {e}")
        results["errors"].append(f"Text: {str(e)}")

    results["fetched"] = list(all_proxies)
    print(f"\n[*] Total unique proxies fetched: {len(all_proxies)}")
    return all_proxies


def test_proxy(proxy):
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

    return {
        'proxy': proxy,
        'http': False,
        'https': False,
        'response_time': None,
        'error': 'Failed'
    }


def test_proxies_parallel(proxies, max_workers=50, test_limit=500):
    """Test multiple proxies in parallel"""
    # Limit the number of proxies to test
    proxies_to_test = list(proxies)[:test_limit] if len(proxies) > test_limit else list(proxies)

    print(f"\n[*] Testing {len(proxies_to_test)} proxies (parallel, {max_workers} workers)...")
    print("=" * 60)

    working = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(test_proxy, proxy): proxy for proxy in proxies_to_test}

        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            results["tested"].append(result)

            if result.get('http') or result.get('https'):
                working.append(result)
                if result.get('http'):
                    results["working_http"].append(result)
                if result.get('https'):
                    results["working_https"].append(result)
                print(f"[{i}/{len(proxies_to_test)}] ✓ {result['proxy']} - HTTP: {result['http']}, Time: {result['response_time']}s, IP: {result.get('ip', 'N/A')}")
            else:
                results["failed"].append(result)
                if i % 50 == 0:
                    print(f"[{i}/{len(proxies_to_test)}] ... tested {i} proxies, {len(working)} working so far")

    return working


def print_report():
    """Print test report"""
    print("\n" + "=" * 60)
    print("SCDN PROXY POOL TEST REPORT")
    print("=" * 60)
    print(f"Source: https://proxy.scdn.io/")
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\n--- Summary ---")
    print(f"Total Proxies Fetched: {len(results['fetched'])}")
    print(f"Total Proxies Tested: {len(results['tested'])}")
    print(f"Working HTTP Proxies: {len(results['working_http'])}")
    print(f"Working HTTPS Proxies: {len(results['working_https'])}")
    print(f"Failed Proxies: {len(results['failed'])}")

    if results['tested']:
        success_rate = len(results['working_http']) / len(results['tested']) * 100
        print(f"Success Rate: {success_rate:.2f}%")

    if results['working_http']:
        print(f"\n--- Top 20 Fastest HTTP Proxies ---")
        sorted_http = sorted(results['working_http'], key=lambda x: x['response_time'])[:20]
        for i, r in enumerate(sorted_http, 1):
            print(f"  {i:2d}. {r['proxy']:25s} - {r['response_time']}s - IP: {r.get('ip', 'N/A')}")

    if results['working_https']:
        print(f"\n--- Top 10 Fastest HTTPS Proxies ---")
        sorted_https = sorted(results['working_https'], key=lambda x: x['response_time'])[:10]
        for i, r in enumerate(sorted_https, 1):
            print(f"  {i:2d}. {r['proxy']:25s} - {r['response_time']}s - IP: {r.get('ip', 'N/A')}")

    # Save to file
    with open('/tmp/scdn_proxy_test_report.txt', 'w') as f:
        f.write("=" * 60 + "\n")
        f.write("SCDN PROXY POOL TEST REPORT\n")
        f.write("=" * 60 + "\n")
        f.write(f"Source: https://proxy.scdn.io/\n")
        f.write(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"\n--- Summary ---\n")
        f.write(f"Total Proxies Fetched: {len(results['fetched'])}\n")
        f.write(f"Total Proxies Tested: {len(results['tested'])}\n")
        f.write(f"Working HTTP Proxies: {len(results['working_http'])}\n")
        f.write(f"Working HTTPS Proxies: {len(results['working_https'])}\n")
        f.write(f"Failed Proxies: {len(results['failed'])}\n")
        if results['tested']:
            f.write(f"Success Rate: {success_rate:.2f}%\n")

        f.write(f"\n--- All Working HTTP Proxies ({len(results['working_http'])}) ---\n")
        sorted_http = sorted(results['working_http'], key=lambda x: x['response_time'])
        for r in sorted_http:
            f.write(f"{r['proxy']} - {r['response_time']}s - IP: {r.get('ip', 'N/A')}\n")

    print(f"\n--- Report saved to /tmp/scdn_proxy_test_report.txt ---")


def main():
    proxies = fetch_scdn_proxies()

    if not proxies:
        print("[!] No proxies fetched!")
        return

    # Test up to 500 proxies (sample from the pool)
    test_proxies_parallel(proxies, test_limit=500)
    print_report()


if __name__ == '__main__':
    main()
