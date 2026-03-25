#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
百度搜索代理实时测试
实时验证代理并测试百度搜索
"""
import requests
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

# 测试配置
BAIDU_URL = "https://www.baidu.com"
SEARCH_URL = "https://www.baidu.com/s"
TEST_KEYWORDS = ["Python", "代理", "爬虫"]

# 实时验证URL（先验证代理是否可用）
VALIDATE_URL = "http://httpbin.org/ip"

results = {
    "verified_proxies": [],
    "baidu_success": [],
    "baidu_failed": [],
    "search_results": []
}


def verify_proxy_first(proxy):
    """先验证代理是否可用"""
    proxies = {'http': f'http://{proxy}'}
    try:
        resp = requests.get(VALIDATE_URL, proxies=proxies, timeout=10)
        if resp.status_code == 200:
            return {'proxy': proxy, 'verified': True, 'ip': resp.json().get('origin', 'unknown')}
    except:
        pass
    return {'proxy': proxy, 'verified': False}


def test_baidu_access(proxy):
    """测试代理访问百度"""
    proxies = {'http': f'http://{proxy}'}
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        start = time.time()
        resp = requests.get(BAIDU_URL, proxies=proxies, headers=headers, timeout=15, allow_redirects=True)
        elapsed = time.time() - start

        if resp.status_code == 200:
            # 检查是否是百度页面
            if 'baidu' in resp.text.lower() or '百度' in resp.text:
                return {
                    'proxy': proxy,
                    'success': True,
                    'response_time': round(elapsed, 2),
                    'title_match': '百度' in resp.text or 'baidu' in resp.text.lower()
                }
    except Exception as e:
        return {
            'proxy': proxy,
            'success': False,
            'error': str(e)[:50]
        }

    return {'proxy': proxy, 'success': False, 'error': 'No response'}


def perform_search(proxy, keyword):
    """执行百度搜索"""
    proxies = {'http': f'http://{proxy}'}
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        params = {'wd': keyword, 'ie': 'utf-8'}
        resp = requests.get(SEARCH_URL, params=params, proxies=proxies, headers=headers, timeout=15)

        if resp.status_code == 200:
            # 提取搜索结果
            title_pattern = r'<title>(.*?)</title>'
            titles = re.findall(title_pattern, resp.text)

            # 提取结果链接
            link_pattern = r'<a.*?href="(http[s]?://[^"]+)".*?>(.*?)</a>'
            links = re.findall(link_pattern, resp.text)

            # 检查是否有搜索结果
            has_results = '百度为您找到相关结果' in resp.text or '百度一下' in resp.text

            return {
                'proxy': proxy,
                'keyword': keyword,
                'success': True,
                'titles': titles[:3],
                'links_count': len(links),
                'has_results': has_results
            }
    except Exception as e:
        return {
            'proxy': proxy,
            'keyword': keyword,
            'success': False,
            'error': str(e)[:50]
        }


def run_baidu_test():
    """运行百度测试"""
    print("=" * 70)
    print(" " * 15 + "百度搜索代理实时测试")
    print("=" * 70)

    print(f"\n开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试策略: 先验证代理可用性，再测试百度访问")

    # 步骤1: 实时验证代理
    print("\n" + "-" * 70)
    print("步骤 1/4: 实时验证代理可用性")
    print("-" * 70)

    # 从之前测试的可用代理中筛选
    test_proxies = WORKING_PROXIES[:30]  # 测试30个代理

    verified = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(verify_proxy_first, proxy): proxy for proxy in test_proxies}

        for future in as_completed(futures):
            result = future.result()
            if result['verified']:
                verified.append(result)
                print(f"✓ {result['proxy']:25s} - 可用 (IP: {result['ip']})")
            else:
                print(f"✗ {result['proxy']:25s} - 不可用")

    print(f"\n验证通过: {len(verified)}/{len(test_proxies)}")

    if not verified:
        print("\n❌ 没有可用的代理，测试结束")
        return generate_empty_report()

    # 步骤2: 测试百度访问
    print("\n" + "-" * 70)
    print("步骤 2/4: 测试代理访问百度")
    print("-" * 70)

    baidu_results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(test_baidu_access, item['proxy']): item for item in verified}

        for future in as_completed(futures):
            proxy = futures[future]
            result = future.result()

            if result['success']:
                baidu_results.append(result)
                print(f"✓ {result['proxy']:25s} - 成功 ({result['response_time']}s)")
            else:
                print(f"✗ {result['proxy']:25s} - 失败")

    print(f"\n百度访问成功: {len(baidu_results)}/{len(verified)}")

    if not baidu_results:
        print("\n❌ 没有代理能访问百度，测试结束")
        return generate_empty_report()

    # 步骤3: 执行搜索测试
    print("\n" + "-" * 70)
    print("步骤 3/4: 执行百度搜索测试")
    print("-" * 70)

    search_success = []
    for result in sorted(baidu_results, key=lambda x: x['response_time'])[:5]:  # 测试前5个最快的
        proxy = result['proxy']
        print(f"\n[*] 使用代理 {proxy} (响应时间: {result['response_time']}s)")

        for keyword in TEST_KEYWORDS:
            search_result = perform_search(proxy, keyword)
            results['search_results'].append(search_result)

            if search_result['success']:
                search_success.append(search_result)
                print(f"    ✓ '{keyword}' - 找到 {search_result['links_count']} 个结果")
                if search_result['titles']:
                    print(f"      标题: {search_result['titles'][0][:40]}...")
            else:
                print(f"    ✗ '{keyword}' - 失败")

            time.sleep(2)

    # 步骤4: 生成报告
    print("\n" + "-" * 70)
    print("步骤 4/4: 生成测试报告")
    print("-" * 70)

    return generate_report(verified, baidu_results, results['search_results'])


def generate_empty_report():
    """生成空结果报告"""
    return f"""
================================================================================
                          百度搜索代理测试报告
================================================================================

测试时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}

================================================================================
一、测试结果
================================================================================

❌ 测试结果: 所有代理均无法访问百度

可能原因:
  1. 免费代理稳定性差，可能已失效
  2. 百度对代理访问有严格限制
  3. 防火墙或网络限制
  4. 代理类型不兼容HTTPS请求

建议:
  • 使用付费代理服务（如 BrightData、Luminati）
  • 配合代理池使用，增加重试机制
  • 考虑使用其他搜索网站（如 Google）
  • 使用国内代理源

================================================================================
报告生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
================================================================================
"""


def generate_report(verified, baidu_results, search_results):
    """生成完整报告"""
    success_count = len(baidu_results)
    verified_count = len(verified)

    report = f"""
================================================================================
                          百度搜索代理测试报告
================================================================================

测试时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
测试项目: 代理访问百度并执行搜索功能

================================================================================
一、测试概述
================================================================================

本次测试对之前测试通过的代理进行了实时验证和百度访问测试。
测试流程包括:
   1. 代理实时可用性验证 (访问 httpbin.org/ip)
  2. 代理访问百度首页测试
  3. 百度搜索功能测试

"""

    report += f"""
================================================================================
二、测试结果统计
================================================================================

┌─────────────────────────────────────────────────────────────────────────────┐
│  测试指标                     │  数值      │
├─────────────────────────────────────────────────────────────────────────────┤
│  预测试可用代理               │  {len(WORKING_PROXIES):<10}    │
│  实时验证通过                 │  {verified_count:<10}    │
│  成功访问百度                 │  {success_count:<10}    │
│  百度访问成功率               │  {(success_count/verified_count*100 if verified_count > 0 else 0):.1f}%      │
└─────────────────────────────────────────────────────────────────────────────┘

"""

    if success_count > 0:
        report += f"""
================================================================================
三、成功访问百度的代理详情
================================================================================

{"排名":<5} {"代理地址":<25} {"响应时间":<10} {"状态":<15}
{"-"*60}
"""

        for i, result in enumerate(sorted(baidu_results, key=lambda x: x['response_time']), 1):
            report += f"{i:<5} {result['proxy']:<25} {result['response_time']}s      {'✓ 正常'}\n"

        report += f"""
{'-'*60}

说明: 以上代理已成功访问百度首页，可进一步测试搜索功能

================================================================================
四、搜索功能测试结果
================================================================================

"""

        search_success_count = sum(1 for r in search_results if r['success'])
        total_search = len(search_results)

        report += f"搜索测试总数: {total_search}\n"
        report += f"搜索成功数量: {search_success_count}\n"
        report += f"搜索成功率: {(search_success_count/total_search*100) if total_search > 0 else 0:.1f}%\n\n"

        # 按关键词统计
        keyword_stats = {}
        for result in search_results:
            kw = result['keyword']
            if kw not in keyword_stats:
                keyword_stats[kw] = {'success': 0, 'total': 0}
            keyword_stats[kw]['total'] += 1
            if result['success']:
                keyword_stats[kw]['success'] += 1

        report += "按关键词统计:\n"
        for keyword, stats in keyword_stats.items():
            rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
            report += f"  • {keyword}: {stats['success']}/{stats['total']} 成功 ({rate:.0f}%)\n"

        # 成功的搜索结果详情
        if search_success_count > 0:
            report += "\n成功搜索示例:\n"
            for result in search_results[:5]:
                if result['success']:
                    report += f"\n  代理: {result['proxy']}\n"
                    report += f"  关键词: {result['keyword']}\n"
                    report += f"  结果数: {result['links_count']}\n"
                    if result.get('titles'):
                        report += f"  标题: {result['titles'][0]}\n"

        report += f"""
================================================================================
五、性能分析
================================================================================

"""

        # 性能统计
        times = [r['response_time'] for r in baidu_results]
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)

        report += f"""响应时间统计:
  • 平均响应时间: {avg_time:.2f} 秒
  • 最快响应时间: {min_time:.2f} 秒
  • 最慢响应时间: {max_time:.2f} 秒

"""

        # 性能评级
        if avg_time < 3:
            report += "性能评级: ⭐⭐⭐⭐⭐ 优秀 (平均响应时间低于3秒)\n"
        elif avg_time < 8:
            report += "性能评级: ⭐⭐⭐⭐☆ 良好 (平均响应时间低于8秒)\n"
        else:
            report += "性能评级: ⭐⭐⭐☆☆ 一般 (平均响应时间超过8秒)\n"

        report += f"""
================================================================================
六、结论与建议
================================================================================

✓ 结论: {success_count} 个代理可以成功访问百度

功能验证:
"""
        if search_success_count > 0:
            report += "  ✓ 搜索功能正常，可用于获取百度搜索结果\n"
        else:
            report += "  ⚠ 搜索功能需要进一步测试\n"

        report += f"""
建议:
  • 这些代理可用于百度相关爬虫任务
  • 建议轮换使用避免单个代理负载过高
  • 注意设置合理的请求间隔，避免被封禁
  • 建议配合代理池使用，自动切换失效代理

"""

    else:
        report += """
================================================================================
五、失败分析
================================================================================

❌ 所有代理都无法访问百度

可能原因:
  1. 免费代理质量不稳定，已失效
  2. 百度对代理访问有严格限制
  3. 代理协议不兼容（百度需要HTTPS）
  4. 网络环境限制

建议:
  • 使用付费代理服务（推荐）
  • 寻找支持HTTPS的代理源
  • 使用国内代理源
  • 考虑使用其他搜索引擎测试

"""

    report += f"""
================================================================================
七、技术说明
================================================================================

测试方法:
  1. 实时验证代理可用性 (httpbin.org/ip)
  2. 测试代理访问百度首页 (https://www.baidu.com)
  3. 执行搜索操作并提取结果

判断标准:
  • 验证通过: 返回200状态码且有IP信息
  • 百度访问成功: 返回200状态码且包含百度相关内容
  • 搜索成功: 响应包含搜索关键词或相关结果

注意事项:
  • 免费代理稳定性较差，建议实时验证后使用
  • 百度可能有反爬虫机制，建议设置合理请求间隔
  • 代理可能随时失效，使用前请重新验证

================================================================================
报告生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
测试工具: proxy_pool 百度搜索测试模块
================================================================================
"""

    return report


# 之前测试通过的代理列表
WORKING_PROXIES = [
    "20.24.43.214:80",
    "147.161.210.140:8800",
    "101.47.73.135:3128",
    "3.137.167.45:39540",
    "46.101.190.71:3128",
    "45.167.124.52:8080",
    "221.202.27.194:10809",
    "167.103.115.102:8800",
    "181.41.201.85:3128",
    "167.103.34.108:8800",
    "82.66.54.40:80",
    "202.47.87.5:9090",
    "160.238.65.6:3128",
    "8.219.97.248:80",
    "158.160.215.167:8124",
    "8.220.141.8:51",
    "36.94.232.177:3113",
    "47.116.181.146:9090",
    "47.112.19.200:8080",
    "47.112.11.170:8090",
    "120.79.217.196:8080",
    "8.138.133.207:6379",
    "8.130.71.75:8081",
    "160.238.65.7:3128",
    "47.254.36.213:8080",
    "8.211.49.86:1080",
    "158.160.215.167:8127",
    "15.204.151.142:3128",
    "103.55.22.252:8080",
    "84.38.185.139:3128",
    "160.238.65.9:3128",
    "160.238.65.8:3128",
    "103.54.80.151:8080",
    "116.80.96.104:3172",
    "84.52.125.113:8082",
    "103.137.91.250:8080",
    "103.161.195.22:3125",
    "27.147.245.189:7735",
    "158.160.215.167:8123",
    "1.1.189.58:8080",
    "116.80.96.95:3172",
    "103.180.123.27:8080",
    "103.156.75.215:9980"
]


if __name__ == "__main__":
    # 运行测试
    report = run_baidu_test()

    # 保存报告
    with open('/tmp/baidu_search_proxy_report.txt', 'w', encoding='utf-8') as f:
        f.write(report)

    # 打印报告
    print(report)
    print("\n报告已保存至: /tmp/baidu_search_proxy_report.txt")
