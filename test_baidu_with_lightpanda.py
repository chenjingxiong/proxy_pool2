#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
使用 Lightpanda 浏览器测试代理访问百度
Lightpanda 是一个轻量级无头浏览器，可以更好地模拟真实用户访问
"""
import subprocess
import json
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# 测试配置
BAIDU_URL = "https://www.baidu.com"
SEARCH_URL = "https://www.baidu.com/s"
LIGHTPANDA_PATH = "/root/.local/bin/lightpanda"
TEST_KEYWORDS = ["Python", "代理"]

# 之前测试成功的代理列表（优先使用响应时间快的）
WORKING_PROXIES = [
    "46.101.190.71:3128",
    "158.160.215.167:8124",
    "160.238.65.7:3128",
    "221.202.27.194:10809",
    "36.94.232.177:3113",
    "8.219.97.248:80",
    "82.66.54.40:80",
    "147.161.210.140:8800",
    "160.238.65.6:3128",
    "181.41.201.85:3128",
    "20.24.43.214:80",
    "167.103.115.102:8800",
    "45.167.124.52:8080",
    "167.103.34.108:8800",
]

# 结果存储
test_results = {
    "successful_proxies": [],
    "failed_proxies": [],
    "search_results": [],
    "start_time": datetime.now()
}


def fetch_with_lightpanda(url, proxy, timeout=30):
    """
    使用 Lightpanda 通过代理获取页面内容

    Args:
        url: 要访问的URL
        proxy: 代理地址 (格式: ip:port)
        timeout: 超时时间（秒）

    Returns:
        dict: 包含状态、内容、响应时间等信息的字典
    """
    start_time = time.time()

    cmd = [
        LIGHTPANDA_PATH,
        "fetch",
        "--dump", "html",
        "--http_proxy", f"http://{proxy}",
        "--insecure_disable_tls_host_verification",
        url
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False
        )

        elapsed_time = time.time() - start_time

        # 检查是否成功
        html_content = result.stdout

        # 检查是否有百度内容
        has_baidu = '百度' in html_content or 'baidu' in html_content.lower()
        has_verification = '安全验证' in html_content or 'verify' in html_content.lower()

        # 检查是否有搜索结果
        has_search_results = '百度为您找到' in html_content or '百度一下' in html_content

        return {
            'success': result.returncode == 0 and len(html_content) > 0,
            'response_time': round(elapsed_time, 2),
            'html_length': len(html_content),
            'has_baidu': has_baidu,
            'has_verification': has_verification,
            'has_search_results': has_search_results,
            'title': extract_title(html_content),
            'returncode': result.returncode,
            'stderr': result.stderr[:200] if result.stderr else ''
        }

    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': 'timeout',
            'response_time': timeout
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)[:100],
            'response_time': time.time() - start_time
        }


def extract_title(html_content):
    """从HTML中提取标题"""
    import re
    match = re.search(r'<title>(.*?)</title>', html_content, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return "无标题"


def test_proxy_baidu_access(proxy):
    """测试代理通过Lightpanda访问百度"""
    print(f"[*] 测试代理 {proxy}...")

    # 1. 测试访问百度首页
    result = fetch_with_lightpanda(BAIDU_URL, proxy, timeout=30)

    result['proxy'] = proxy

    if result['success'] and result['has_baidu']:
        result['can_access_baidu'] = True
        status = "✓ 成功"
        if result['has_verification']:
            status += " (触发验证)"
        print(f"    {status} - {result['response_time']}s - 标题: {result['title'][:30]}")
        test_results['successful_proxies'].append(result)
    else:
        result['can_access_baidu'] = False
        error = result.get('error', result.get('stderr', '未知错误'))[:50]
        print(f"    ✗ 失败 - {error}")
        test_results['failed_proxies'].append(result)

    return result


def test_baidu_search(proxy, keyword):
    """测试通过代理执行百度搜索"""
    search_url = f"{SEARCH_URL}?wd={keyword}&ie=utf-8"

    print(f"    [*] 搜索 '{keyword}'...")

    result = fetch_with_lightpanda(search_url, proxy, timeout=30)

    result['proxy'] = proxy
    result['keyword'] = keyword

    if result['success']:
        # 统计搜索结果数量
        import re
        result_count = 0
        if '百度为您找到相关结果' in result.get('html', ''):
            match = re.search(r'百度为您找到相关结果约([0-9,]+)个', result.get('html', ''))
            if match:
                result_count = match.group(1)

        result['result_count'] = result_count
        test_results['search_results'].append(result)

        status = "✓" if result['has_search_results'] else "⚠"
        print(f"        {status} 响应: {result['response_time']}s - 结果: {result_count or '未知'} - {result['title'][:30]}")
    else:
        print(f"        ✗ 失败 - {result.get('error', '未知错误')[:30]}")
        test_results['search_results'].append(result)

    time.sleep(2)  # 避免请求过快
    return result


def run_comprehensive_test():
    """运行综合测试"""
    print("=" * 70)
    print(" " * 15 + "Lightpanda 浏览器代理百度测试")
    print("=" * 70)
    print()
    print(f"开始时间: {test_results['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试代理数量: {len(WORKING_PROXIES)}")
    print(f"测试工具: Lightpanda 无头浏览器")
    print()

    # 步骤1: 测试所有代理访问百度首页
    print("-" * 70)
    print("步骤 1/2: 测试代理通过 Lightpanda 访问百度首页")
    print("-" * 70)
    print()

    # 使用线程池并发测试
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(test_proxy_baidu_access, proxy): proxy for proxy in WORKING_PROXIES}

        for future in as_completed(futures):
            future.result()  # 结果已在test_proxy_baidu_access中处理

    print()

    # 步骤2: 使用成功代理执行搜索
    print("-" * 70)
    print("步骤 2/2: 使用成功代理执行百度搜索")
    print("-" * 70)
    print()

    if not test_results['successful_proxies']:
        print("没有成功访问百度的代理，跳过搜索测试")
        return test_results

    # 使用前5个成功的代理进行搜索测试
    successful = sorted(test_results['successful_proxies'], key=lambda x: x['response_time'])[:5]

    for result in successful:
        proxy = result['proxy']
        print(f"[*] 使用代理 {proxy} (响应时间: {result['response_time']}s)")

        for keyword in TEST_KEYWORDS:
            test_baidu_search(proxy, keyword)

        print()

    return test_results


def generate_report():
    """生成测试报告"""
    results = run_comprehensive_test()

    success_count = len(results['successful_proxies'])
    failed_count = len(results['failed_proxies'])
    total_count = len(WORKING_PROXIES)
    success_rate = (success_count / total_count * 100) if total_count > 0 else 0

    # 统计触发验证的代理
    verification_count = sum(1 for r in results['successful_proxies'] if r.get('has_verification'))

    # 统计搜索结果
    search_success = sum(1 for r in results.get('search_results', []) if r.get('has_search_results'))

    report = f"""
================================================================================
                   Lightpanda 浏览器代理百度测试报告
================================================================================

测试时间: {results['start_time'].strftime('%Y年%m月%d日 %H:%M:%S')}
测试工具: Lightpanda 无头浏览器
测试项目: 通过代理访问百度并执行搜索功能

================================================================================
一、测试概述
================================================================================

本次测试使用 Lightpanda 无头浏览器，通过代理IP访问百度首页并执行搜索。
Lightpanda 是一个轻量级的无头浏览器，能够更好地模拟真实用户访问行为，
有助于绕过基本的反爬虫检测。

测试流程:
  1. 使用 Lightpanda 通过代理访问百度首页
  2. 检查页面内容验证访问成功
  3. 执行百度搜索操作并提取结果

================================================================================
二、测试结果统计
================================================================================

┌─────────────────────────────────────────────────────────────────────────────┐
│  测试指标                     │  数值      │  占比    │
├─────────────────────────────────────────────────────────────────────────────┤
│  测试代理总数                 │  {total_count:<10}    │   100%   │
│  成功访问百度                 │  {success_count:<10}    │   {success_rate:.1f}%   │
│  访问失败                     │  {failed_count:<10}    │   {(100-success_rate):.1f}%   │
│  触发安全验证                 │  {verification_count:<10}    │   -       │
│  搜索测试成功                 │  {search_success:<10}    │   -       │
└─────────────────────────────────────────────────────────────────────────────┘

成功率分析: {"优秀" if success_rate >= 70 else "良好" if success_rate >= 50 else "一般" if success_rate >= 30 else "较差"} - {success_rate:.1f}% 的代理可以成功访问百度

================================================================================
三、成功代理详情
================================================================================

{"排名":<5} {"代理地址":<25} {"响应时间":<10} {"状态":<20}
{"-"*65}
"""

    # 添加成功代理详情
    for i, result in enumerate(sorted(results['successful_proxies'], key=lambda x: x['response_time']), 1):
        status = "✓ 正常"
        if result.get('has_verification'):
            status = "⚠ 触发验证"
        title = result.get('title', '无标题')[:15]
        report += f"{i:<5} {result['proxy']:<25} {result['response_time']}s      {status} {title}\n"

    report += f"""
{'-'*65}

说明: 以上为成功访问百度的代理，按响应时间排序

================================================================================
四、搜索功能测试
================================================================================

"""

    if results.get('search_results'):
        report += f"搜索测试总数: {len(results['search_results'])}\n"

        # 按关键词统计
        keyword_stats = {}
        for result in results['search_results']:
            kw = result.get('keyword', 'unknown')
            if kw not in keyword_stats:
                keyword_stats[kw] = {'success': 0, 'total': 0}
            keyword_stats[kw]['total'] += 1
            if result.get('has_search_results'):
                keyword_stats[kw]['success'] += 1

        report += "按关键词统计:\n"
        for keyword, stats in keyword_stats.items():
            rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
            report += f"  • {keyword}: {stats['success']}/{stats['total']} 成功 ({rate:.0f}%)\n"

        report += "\n搜索结果示例:\n"
        for result in results['search_results'][:5]:
            if result.get('success'):
                report += f"\n  代理: {result['proxy']}\n"
                report += f"  关键词: {result.get('keyword', 'N/A')}\n"
                report += f"  响应时间: {result['response_time']}s\n"
                report += f"  标题: {result.get('title', 'N/A')}\n"
                if result.get('result_count'):
                    report += f"  结果数量: {result['result_count']}\n"

    report += f"""
================================================================================
五、性能分析
================================================================================
"""

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
        if avg_time < 5:
            report += "性能评级: ⭐⭐⭐⭐⭐ 优秀 (平均响应时间低于5秒)\n"
        elif avg_time < 10:
            report += "性能评级: ⭐⭐⭐⭐☆ 良好 (平均响应时间低于10秒)\n"
        elif avg_time < 20:
            report += "性能评级: ⭐⭐⭐☆☆ 一般 (平均响应时间低于20秒)\n"
        else:
            report += "性能评级: ⭐⭐☆☆☆ 较慢 (平均响应时间超过20秒)\n"

    report += f"""
================================================================================
六、结论与建议
================================================================================

"""

    if success_rate >= 50:
        report += f"""✓ 结论: 使用 Lightpanda 浏览器，{success_count} 个代理可以成功访问百度

优势分析:
  • Lightpanda 作为无头浏览器，能够更好地模拟真实用户行为
  • 相比直接HTTP请求，可以执行JavaScript并渲染完整页面
  • 部分情况下可能绕过基础的反爬虫检测

功能验证:
"""
        if search_success > 0:
            report += "  ✓ 搜索功能正常，能够获取搜索结果\n"
        else:
            report += "  ⚠ 搜索功能需要进一步测试\n"

        if verification_count > 0:
            report += f"  ⚠ {verification_count} 个代理触发了百度的安全验证页面\n"

        report += """
建议:
  • 这些代理可用于百度相关爬虫任务
  • 建议配合 Lightpanda 或其他无头浏览器使用
  • 注意设置合理的请求间隔，避免被封禁
  • 对于触发验证的代理，可能需要额外的验证码处理

"""

    else:
        report += f"""⚠ 结论: 代理成功率较低，可能需要优化

可能原因:
  • 百度对无头浏览器访问有额外检测
  • 代理IP质量不稳定
  • 需要更真实的浏览器指纹

建议:
  • 尝试使用付费代理服务
  • 配合更多浏览器伪装技术
  • 考虑使用代理池自动切换

"""

    report += f"""
================================================================================
七、技术说明
================================================================================

测试方法:
  1. 使用 Lightpanda 无头浏览器
  2. 通过 HTTP 代理访问百度
  3. 禁用 TLS 主机验证（某些代理需要）
  4. 获取并分析渲染后的HTML内容

Lightpanda 优势:
  • 轻量级，资源占用低
  • 支持JavaScript执行
  • 支持代理配置
  • 可获取渲染后的完整页面

命令示例:
  lightpanda fetch --dump html --http_proxy http://ip:port \\
    --insecure_disable_tls_host_verification https://www.baidu.com

================================================================================
报告生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
测试工具: proxy_pool + Lightpanda
================================================================================
"""

    return report


if __name__ == "__main__":
    # 生成并保存报告
    report = generate_report()

    # 保存到文件
    report_path = '/tmp/baidu_lightpanda_proxy_report.txt'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)

    # 打印报告
    print(report)
    print(f"\n报告已保存至: {report_path}")
