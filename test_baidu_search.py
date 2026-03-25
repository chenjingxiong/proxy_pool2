#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
百度搜索代理测试
测试可用代理访问百度并进行搜索
"""
import requests
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# 百度搜索URL
BAIDU_URL = "https://www.baidu.com"
SEARCH_URL = "https://www.baidu.com/s"

# 从之前测试中获取的可用代理
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

# 测试关键词
TEST_KEYWORDS = [
    "Python",
    "代理IP",
    "爬虫",
    "人工智能"
]

# 结果存储
test_results = {
    "successful_proxies": [],
    "failed_proxies": [],
    "search_results": {},
    "start_time": datetime.now()
}


def test_proxy_baidu(proxy):
    """测试代理访问百度"""
    proxies = {
        'http': f'http://{proxy}',
        'https': f'http://{proxy}'
    }

    result = {
        'proxy': proxy,
        'can_access_baidu': False,
        'can_search': False,
        'response_time': None,
        'error': None
    }

    try:
        # 1. 测试访问百度首页
        start = time.time()
        resp = requests.get(BAIDU_URL, proxies=proxies, timeout=15, allow_redirects=True)
        access_time = time.time() - start

        if resp.status_code == 200 and '百度' in resp.text:
            result['can_access_baidu'] = True
            result['response_time'] = round(access_time, 2)

            # 2. 测试搜索功能
            search_params = {'wd': TEST_KEYWORDS[0], 'ie': 'utf-8'}
            search_start = time.time()
            search_resp = requests.get(SEARCH_URL, params=search_params, proxies=proxies, timeout=15)
            search_time = time.time() - search_start

            if search_resp.status_code == 200 and TEST_KEYWORDS[0] in search_resp.text:
                result['can_search'] = True
                result['search_time'] = round(search_time, 2)

                # 提取搜索结果数量
                if '百度为您找到相关结果' in search_resp.text:
                    result['found_results'] = True
                elif '百度一下' in search_resp.text:
                    result['found_results'] = True

        return result

    except Exception as e:
        result['error'] = str(e)
        return result


def perform_detailed_search(proxy, keyword):
    """使用代理执行详细搜索"""
    proxies = {
        'http': f'http://{proxy}',
        'https': f'http://{proxy}'
    }

    try:
        params = {
            'wd': keyword,
            'ie': 'utf-8',
            'rn': 10,
            'pn': 0
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        resp = requests.get(SEARCH_URL, params=params, proxies=proxies, headers=headers, timeout=15)

        if resp.status_code == 200:
            # 提取搜索结果
            import re
            title_pattern = r'<title>(.*?)</title>'
            titles = re.findall(title_pattern, resp.text)

            result_link_pattern = r'<a.*?href="(http[s]?://[^"]+)".*?>(.*?)</a>'
            links = re.findall(result_link_pattern, resp.text)

            return {
                'keyword': keyword,
                'status': 'success',
                'titles': titles[:5],
                'links_count': len(links)
            }
    except Exception as e:
        return {
            'keyword': keyword,
            'status': 'error',
            'error': str(e)
        }


def run_comprehensive_test():
    """运行综合测试"""
    print("=" * 70)
    print(" " * 15 + "百度搜索代理测试")
    print("=" * 70)

    print(f"\n开始时间: {test_results['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试代理数量: {len(WORKING_PROXIES)}")
    print(f"测试关键词: {', '.join(TEST_KEYWORDS)}")

    # 步骤1: 测试所有代理访问百度
    print("\n" + "-" * 70)
    print("步骤 1/3: 测试代理访问百度首页")
    print("-" * 70)

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(test_proxy_baidu, proxy): proxy for proxy in WORKING_PROXIES}

        for future in as_completed(futures):
            result = future.result()
            proxy = result['proxy']

            if result['can_access_baidu']:
                test_results['successful_proxies'].append(result)
                print(f"✓ {proxy:25s} - 访问成功 ({result['response_time']}s)")
            else:
                test_results['failed_proxies'].append(result)
                error_msg = result.get('error') or 'Unknown'
                print(f"✗ {proxy:25s} - 访问失败 ({error_msg[:30]})")

    # 步骤2: 统计结果
    print("\n" + "-" * 70)
    print("步骤 2/3: 统计测试结果")
    print("-" * 70)

    success_count = len(test_results['successful_proxies'])
    failed_count = len(test_results['failed_proxies'])
    success_rate = (success_count / len(WORKING_PROXIES) * 100) if WORKING_PROXIES else 0

    print(f"\n总代理数量: {len(WORKING_PROXIES)}")
    print(f"访问成功: {success_count}")
    print(f"访问失败: {failed_count}")
    print(f"成功率: {success_rate:.2f}%")

    # 步骤3: 使用成功代理执行搜索
    print("\n" + "-" * 70)
    print("步骤 3/3: 使用成功代理执行搜索")
    print("-" * 70)

    search_success = 0
    for result in test_results['successful_proxies'][:10]:  # 测试前10个
        proxy = result['proxy']
        print(f"\n[*] 使用代理 {proxy} 搜索...")

        for keyword in TEST_KEYWORDS[:2]:  # 每个代理搜索2个关键词
            search_result = perform_detailed_search(proxy, keyword)

            if search_result['status'] == 'success':
                search_success += 1
                print(f"    ✓ '{keyword}' - 找到 {search_result['links_count']} 个结果")
                if search_result['titles']:
                    print(f"      标题示例: {search_result['titles'][0][:50]}...")
            else:
                print(f"    ✗ '{keyword}' - 搜索失败: {search_result.get('error', 'Unknown')}")

            time.sleep(1)  # 避免请求过快

        if search_success >= 5:
            break

    return test_results


def generate_chinese_report():
    """生成中文测试报告"""
    results = run_comprehensive_test()

    report = f"""
================================================================================
                          百度搜索代理测试报告
================================================================================

测试时间: {results['start_time'].strftime('%Y年%m月%d日 %H:%M:%S')}
测试项目: 代理访问百度并执行搜索功能

================================================================================
一、测试概述
================================================================================

本次测试共使用了 {len(WORKING_PROXIES)} 个预先测试可用的代理IP，
对这些代理进行百度访问和搜索功能的综合测试。

测试内容包括：
  1. 代理访问百度首页的能力
  2. 代理执行百度搜索的能力
  3. 搜索结果的完整性和准确性

================================================================================
二、测试结果统计
================================================================================

┌─────────────────────────────────────────────────────────────────────────────┐
│  测试指标                     │  数值      │  占比    │
├─────────────────────────────────────────────────────────────────────────────┤
│  测试代理总数                 │  {len(WORKING_PROXIES):<10}    │   100%   │
│  成功访问百度                 │  {len(results['successful_proxies']):<10}    │   {len(results['successful_proxies'])/len(WORKING_PROXIES)*100:.1f}%   │
│  访问失败                     │  {len(results['failed_proxies']):<10}    │   {len(results['failed_proxies'])/len(WORKING_PROXIES)*100:.1f}%   │
└─────────────────────────────────────────────────────────────────────────────┘

成功率分析: {""}
{"成功" if len(results['successful_proxies'])/len(WORKING_PROXIES) >= 0.5 else "较低"} {'✓' if len(results['successful_proxies']) > 0 else '✗'} - {len(results['successful_proxies'])/len(WORKING_PROXIES)*100:.1f}% 的代理能够成功访问百度

================================================================================
三、成功代理详情
================================================================================

{"排名":<5} {"代理地址":<25} {"响应时间":<10} {"搜索功能":<10}
{"-"*60}
"""

    # 添加成功代理详情
    for i, result in enumerate(sorted(results['successful_proxies'], key=lambda x: x['response_time'])[:15], 1):
        search_status = "✓ 可用" if result.get('can_search') else "✗ 不可用"
        report += f"{i:<5} {result['proxy']:<25} {result['response_time']}s      {search_status}\n"

    report += f"""
{'-'*60}

注: 以上为响应时间最快的 15 个成功代理

================================================================================
四、失败代理分析
================================================================================

"""

    # 失败原因统计
    error_types = {}
    for result in results['failed_proxies'][:10]:
        error = result.get('error', 'Unknown')[:30]
        error_types[error] = error_types.get(error, 0) + 1

    for error, count in error_types.items():
        report += f"  • {error}: {count} 个代理\n"

    report += f"""
{'-'*60}
注: 以上为主要失败原因统计（仅显示前10个）

================================================================================
五、搜索功能测试
================================================================================

测试关键词: {', '.join(TEST_KEYWORDS)}

"""

    # 搜索功能统计
    can_search_count = sum(1 for r in results['successful_proxies'] if r.get('can_search'))
    report += f"支持搜索的代理数: {can_search_count} / {len(results['successful_proxies'])}\n\n"

    if can_search_count > 0:
        report += "✓ 搜索功能正常，代理可以执行百度搜索并返回结果\n"
    else:
        report += "✗ 搜索功能异常，所有代理都无法完成搜索\n"

    report += f"""
================================================================================
六、性能分析
================================================================================

"""

    # 响应时间分析
    if results['successful_proxies']:
        times = [r['response_time'] for r in results['successful_proxies']]
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)

        report += f"""响应时间统计:
  • 平均响应时间: {avg_time:.2f} 秒
  • 最快响应时间: {min_time:.2f} 秒
  • 最慢响应时间: {max_time:.2f} 秒

"""

        # 性能等级评价
        if avg_time < 2:
            report += "性能评级: ⭐⭐⭐⭐⭐ 优秀 (平均响应时间低于2秒)\n"
        elif avg_time < 5:
            report += "性能评级: ⭐⭐⭐⭐☆ 良好 (平均响应时间低于5秒)\n"
        elif avg_time < 10:
            report += "性能评级: ⭐⭐⭐☆☆ 一般 (平均响应时间低于10秒)\n"
        else:
            report += "性能评级: ⭐⭐☆☆☆ 较慢 (平均响应时间超过10秒)\n"

    report += f"""
================================================================================
七、结论与建议
================================================================================

"""

    success_rate = len(results['successful_proxies']) / len(WORKING_PROXIES) * 100

    if success_rate >= 50:
        report += """✓ 结论: 代理质量优秀，大部分代理可以正常访问百度

建议:
  • 这些代理可用于百度搜索相关任务
  • 建议轮换使用以避免单个代理负载过高
  • 可用于爬虫项目中获取百度搜索结果

"""
    elif success_rate >= 20:
        report += """⚠ 结论: 代理质量一般，约三分之一的代理可用

建议:
  • 可以使用，但需要增加重试机制
  • 建议配合代理验证功能使用
  • 注意代理的稳定性可能随时变化

"""
    else:
        report += """✗ 结论: 代理质量较差，大部分代理无法访问百度

建议:
  • 不建议用于百度搜索任务
  • 需要寻找更稳定的代理源
  • 建议使用付费代理服务

"""

    report += f"""
================================================================================
八、技术说明
================================================================================

测试方法:
  1. 使用 Python requests 库发送 HTTP 请求
  2. 通过代理服务器访问百度首页
  3. 检查响应状态码和页面内容验证
  4. 执行搜索操作并提取结果

判断标准:
  • 成功访问: HTTP 200 状态码且页面包含"百度"字样
  • 搜索成功: 响应包含搜索关键词或相关结果

注意事项:
  • 免费代理稳定性较差，可能随时失效
  • 建议在使用前重新验证代理可用性
  • 避免频繁请求同一代理以防被封禁

================================================================================
报告生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
报告生成工具: proxy_pool 百度搜索测试模块
================================================================================
"""

    return report


if __name__ == "__main__":
    # 生成并保存报告
    report = generate_chinese_report()

    # 保存到文件
    with open('/tmp/baidu_search_proxy_report.txt', 'w', encoding='utf-8') as f:
        f.write(report)

    # 打印报告
    print(report)
    print("\n报告已保存至: /tmp/baidu_search_proxy_report.txt")
