# -*- coding: utf-8 -*-
# !/usr/bin/env python
"""
-------------------------------------------------
   File Name：     ProxyApi.py
   Description :   WebApi
   Author :       JHao
   date：          2016/12/4
-------------------------------------------------
   Change Activity:
                   2016/12/04: WebApi
                   2019/08/14: 集成Gunicorn启动方式
                   2020/06/23: 新增pop接口
                   2022/07/21: 更新count接口
-------------------------------------------------
"""
__author__ = 'JHao'

import platform
import time as _time
import json as _json
from flask import Flask, jsonify, request, render_template, Response

from util.six import iteritems
from helper.proxy import Proxy
from handler.proxyHandler import ProxyHandler
from handler.configHandler import ConfigHandler
from handler.refreshHandler import RefreshHandler

app = Flask(__name__, template_folder='templates')
conf = ConfigHandler()
proxy_handler = ProxyHandler()


class JsonResponse(Response):
    @classmethod
    def force_type(cls, response, environ=None):
        if isinstance(response, (dict, list)):
            response = jsonify(response)

        return super(JsonResponse, cls).force_type(response, environ)


app.response_class = JsonResponse

api_list = [
    {"url": "/get", "params": "type: ''https'|''", "desc": "get a proxy"},
    {"url": "/pop", "params": "", "desc": "get and delete a proxy"},
    {"url": "/delete", "params": "proxy: 'e.g. 127.0.0.1:8080'", "desc": "delete an unable proxy"},
    {"url": "/all", "params": "type: ''https'|''", "desc": "get all proxy from proxy pool"},
    {"url": "/count", "params": "", "desc": "return proxy count"},
    {"url": "/get_status", "params": "", "desc": "return proxy pool status info"},
    {"url": "/proxy_use_count", "params": "limit: int (default 10)", "desc": "proxy use count ranking"},
    {"url": "/export", "params": "format: 'json'|'txt', available: '1'|'0', https: '1'|'0'", "desc": "export proxies"},
    # 'refresh': 'refresh proxy pool',
]


@app.route('/')
def index():
    return render_template('dashboard.html')


@app.route('/get/')
def get():
    https = request.args.get("type", "").lower() == 'https'
    proxy = proxy_handler.get(https)
    if proxy:
        proxy_handler.incrementUseCount(proxy)
        return proxy.to_dict
    return {"code": 0, "src": "no proxy"}


@app.route('/pop/')
def pop():
    https = request.args.get("type", "").lower() == 'https'
    proxy = proxy_handler.pop(https)
    return proxy.to_dict if proxy else {"code": 0, "src": "no proxy"}


@app.route('/refresh/')
def refresh():
    # TODO refresh会有守护程序定时执行，由api直接调用性能较差，暂不使用
    return 'success'


@app.route('/all/')
def getAll():
    https = request.args.get("type", "").lower() == 'https'
    proxies = proxy_handler.getAll(https)
    return jsonify([_.to_dict for _ in proxies])


@app.route('/delete/', methods=['GET'])
def delete():
    proxy = request.args.get('proxy')
    status = proxy_handler.delete(Proxy(proxy))
    return {"code": 0, "src": status}


@app.route('/count/')
def getCount():
    proxies = proxy_handler.getAll()
    http_type_dict = {}
    source_dict = {}
    for proxy in proxies:
        http_type = 'https' if proxy.https else 'http'
        http_type_dict[http_type] = http_type_dict.get(http_type, 0) + 1
        for source in proxy.source.split('/'):
            source_dict[source] = source_dict.get(source, 0) + 1
    return {"http_type": http_type_dict, "source": source_dict, "count": len(proxies)}


@app.route('/get_status/')
def getStatus():
    """ 返回代理池状态信息 """
    proxies = proxy_handler.getAll()
    total = len(proxies)

    # HTTP/HTTPS distribution
    http_count = 0
    https_count = 0
    # Source distribution
    source_dict = {}
    # Speed statistics
    speeds = []
    # Health: proxies with last_status=True
    healthy_count = 0

    for proxy in proxies:
        if proxy.https:
            https_count += 1
        else:
            http_count += 1
        for source in proxy.source.split('/'):
            if source:
                source_dict[source] = source_dict.get(source, 0) + 1
        if proxy.speed and proxy.speed > 0:
            speeds.append(proxy.speed)
        if proxy.last_status is True:
            healthy_count += 1

    avg_speed = round(sum(speeds) / len(speeds), 3) if speeds else 0.0
    min_speed = round(min(speeds), 3) if speeds else 0.0
    max_speed = round(max(speeds), 3) if speeds else 0.0

    return {
        "total": total,
        "http_count": http_count,
        "https_count": https_count,
        "healthy_count": healthy_count,
        "unhealthy_count": total - healthy_count,
        "source_count": source_dict,
        "speed": {
            "avg": avg_speed,
            "min": min_speed,
            "max": max_speed,
        },
        "timestamp": _time.strftime("%Y-%m-%d %H:%M:%S"),
    }


@app.route('/proxy_use_count/')
def proxyUseCount():
    """ 返回代理使用次数排行 """
    limit = request.args.get("limit", 10, type=int)
    if limit < 1:
        limit = 10
    if limit > 100:
        limit = 100
    proxies = proxy_handler.getUseCountRanking(limit)
    return {
        "ranking": [_.to_dict for _ in proxies],
        "limit": limit
    }


@app.route('/export/')
def exportProxies():
    """
    导出代理列表
    params:
      format: 'json' (default) or 'txt'
      available: '1' to only export available proxies (last_status=True)
      https: '1' to only export HTTPS proxies
    """
    export_format = request.args.get("format", "json").lower().strip()
    only_available = request.args.get("available", "0") == "1"
    only_https = request.args.get("https", "0") == "1"

    # Get filtered proxies
    https_flag = True if only_https else False
    proxies = proxy_handler.getAll(https=https_flag)

    # Apply additional filters
    filtered = []
    for proxy in proxies:
        if only_available and proxy.last_status is not True:
            continue
        if only_https and not proxy.https:
            continue
        filtered.append(proxy)

    if export_format == 'txt':
        # Plain text: one proxy per line (ip:port)
        lines = [p.proxy for p in filtered]
        txt_content = "\n".join(lines)
        return Response(txt_content, mimetype='text/plain',
                        headers={"Content-Disposition": "attachment; filename=proxies.txt"})
    else:
        # JSON format
        result = [p.to_dict for p in filtered]
        response = app.response_class(
            response=_json.dumps(result, ensure_ascii=False, indent=2),
            status=200,
            mimetype='application/json'
        )
        response.headers["Content-Disposition"] = "attachment; filename=proxies.json"
        return response


@app.route('/refresh_pool/')
def refreshPool():
    """ 手动触发代理池刷新（异步执行，避免阻塞 gunicorn worker）"""
    import threading
    try:
        def _bg_refresh():
            try:
                refresh_handler = RefreshHandler()
                refresh_handler.refresh()
            except Exception as e:
                from handler.logHandler import LogHandler
                LogHandler("refresh").error("Manual refresh failed: {}".format(e))

        thread = threading.Thread(target=_bg_refresh, daemon=True)
        thread.start()
        return {"code": 1, "msg": "refresh triggered in background"}
    except Exception as e:
        return {"code": 0, "msg": str(e)}


@app.route('/ai_search/')
def aiSearch():
    """ 手动触发AI代理搜索 """
    _conf = ConfigHandler()
    if not _conf.aiSearchEnabled:
        return {"code": 0, "msg": "AI search is not enabled. Set AI_API_KEY env var."}
    try:
        from helper.aiSearch import AISearch
        from util.six import Queue
        from helper.check import Checker
        ai = AISearch()
        proxies = ai.search_proxies()
        proxy_queue = Queue()
        for proxy_str in proxies:
            proxy_queue.put(Proxy(proxy_str, source="aiProxySearch"))
        queue_size = proxy_queue.qsize()
        if queue_size > 0:
            import threading
            threading.Thread(
                target=lambda q: Checker("raw", q),
                args=(proxy_queue,),
                daemon=True
            ).start()
        return {
            "code": 1,
            "msg": "AI search complete",
            "proxies_found": len(proxies),
            "proxies_validated": queue_size,
        }
    except Exception as e:
        return {"code": 0, "msg": str(e)}


# ===================== Dashboard API =====================

@app.route('/api/sources/')
def apiSources():
    """返回所有代理源配置及统计"""
    from handler.sourceHandler import SourceLoader
    loader = SourceLoader()
    all_sources = loader.get_all_sources()

    # 统计每个源贡献的代理数量
    proxies = proxy_handler.getAll()
    source_contrib = {}
    for proxy in proxies:
        for src in proxy.source.split('/'):
            src = src.strip()
            if src:
                source_contrib[src] = source_contrib.get(src, 0) + 1

    result = []
    for s in all_sources:
        result.append({
            "name": s.name,
            "type": s.type,
            "description": s.description,
            "category": s.category,
            "enabled": s.enabled,
            "url": s.url or "",
            "source_file": s.source_file,
            "contributed": source_contrib.get(s.name, 0),
        })

    # 添加已贡献但不在INI中的源（如aiProxySearch）
    ini_names = {s.name for s in all_sources}
    for src, count in source_contrib.items():
        if src not in ini_names:
            result.append({
                "name": src,
                "type": "dynamic",
                "description": src,
                "category": "http",
                "enabled": True,
                "url": "",
                "source_file": "",
                "contributed": count,
            })

    return {"sources": result, "total": len(result)}


@app.route('/api/dashboard/status/')
def apiDashboardStatus():
    """增强版代理池状态（含速度分布、健康率）"""
    proxies = proxy_handler.getAll()
    total = len(proxies)

    http_count = 0
    https_count = 0
    healthy_count = 0
    speeds = []
    speed_buckets = {"<0.5s": 0, "0.5-1s": 0, "1-2s": 0, "2-5s": 0, ">5s": 0}
    source_dict = {}
    check_count_sum = 0
    fail_count_sum = 0

    for proxy in proxies:
        if proxy.https:
            https_count += 1
        else:
            http_count += 1
        if proxy.last_status is True:
            healthy_count += 1
        if proxy.speed and proxy.speed > 0:
            speeds.append(proxy.speed)
            if proxy.speed < 0.5:
                speed_buckets["<0.5s"] += 1
            elif proxy.speed < 1:
                speed_buckets["0.5-1s"] += 1
            elif proxy.speed < 2:
                speed_buckets["1-2s"] += 1
            elif proxy.speed < 5:
                speed_buckets["2-5s"] += 1
            else:
                speed_buckets[">5s"] += 1
        for source in proxy.source.split('/'):
            if source:
                source_dict[source] = source_dict.get(source, 0) + 1
        if proxy.check_count:
            check_count_sum += proxy.check_count
        if proxy.fail_count:
            fail_count_sum += proxy.fail_count

    top_sources = sorted(source_dict.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "total": total,
        "http_count": http_count,
        "https_count": https_count,
        "healthy_count": healthy_count,
        "unhealthy_count": total - healthy_count,
        "health_rate": round(healthy_count / total * 100, 1) if total else 0,
        "speed": {
            "avg": round(sum(speeds) / len(speeds), 3) if speeds else 0,
            "min": round(min(speeds), 3) if speeds else 0,
            "max": round(max(speeds), 3) if speeds else 0,
            "distribution": speed_buckets,
        },
        "top_sources": [{"name": n, "count": c} for n, c in top_sources],
        "total_check_count": check_count_sum,
        "total_fail_count": fail_count_sum,
        "timestamp": _time.strftime("%Y-%m-%d %H:%M:%S"),
    }


@app.route('/api/dashboard/activity/')
def apiDashboardActivity():
    """每日动态、AI搜索历史、调度信息"""
    import redis as _redis
    activity = {
        "ai_search_log": [],
        "daily_counts": [],
    }

    try:
        conn = _redis.Redis.from_url(conf.dbConn, decode_responses=True)

        # AI搜索历史
        logs = conn.lrange('proxy_pool:ai_search_log', 0, 29)
        activity["ai_search_log"] = [_json.loads(l) for l in logs if l]

        # 每日代理数（基于key pattern proxy_pool:daily:YYYY-MM-DD）
        daily = {}
        for key in conn.scan_iter('proxy_pool:daily:*'):
            date_str = key.split(':')[-1]
            daily[date_str] = int(conn.get(key) or 0)
        activity["daily_counts"] = [
            {"date": d, "count": c} for d, c in sorted(daily.items(), reverse=True)[:30]
        ]
    except Exception:
        pass

    activity["timestamp"] = _time.strftime("%Y-%m-%d %H:%M:%S")
    return activity


# ===================== AI Config API =====================

@app.route('/api/ai/config/', methods=['GET'])
def apiAiConfigGet():
    """获取当前 AI 配置（API Key 脱敏）"""
    from handler.configHandler import _get_env_sourced_keys
    _conf = ConfigHandler()
    key = _conf.aiApiKey
    masked = '****' + key[-4:] if len(key) > 4 else ('****' if key else '')
    return {
        "api_key_masked": masked,
        "api_key_set": bool(key),
        "api_base_url": _conf.aiApiBaseUrl,
        "model": _conf.aiModel,
        "search_enabled": _conf.aiSearchEnabled,
        "search_hour": _conf.aiSearchHour,
        "max_sources": _conf.aiMaxSources,
        "api_timeout": _conf.aiApiTimeout,
        "env_sourced": _get_env_sourced_keys(),
    }


@app.route('/api/ai/config/', methods=['POST'])
def apiAiConfigPost():
    """保存 AI 配置到 INI 文件"""
    data = request.get_json(force=True)
    # 如果 api_key 为 ****掩码则保留原值
    if data.get('api_key', '') in ('', '****') or data.get('api_key', '').startswith('****'):
        _conf = ConfigHandler()
        data['api_key'] = _conf.aiApiKey
    ConfigHandler.save_ai_config(data)
    return {"code": 1, "msg": "配置已保存"}


@app.route('/api/ai/search/', methods=['POST'])
def apiAiSearch():
    """手动触发 AI 代理搜索"""
    _conf = ConfigHandler()
    if not _conf.aiApiKey:
        return {"code": 0, "msg": "AI search disabled: API Key 未配置"}
    try:
        from helper.aiSearch import AISearch
        from util.six import Queue
        from helper.check import Checker
        ai = AISearch()
        proxies = ai.search_proxies()
        proxy_queue = Queue()
        for proxy_str in proxies:
            proxy_queue.put(Proxy(proxy_str, source="aiProxySearch"))
        queue_size = proxy_queue.qsize()
        if queue_size > 0:
            import threading
            checker_thread = threading.Thread(
                target=lambda q: Checker("raw", q),
                args=(proxy_queue,),
                daemon=True
            )
            checker_thread.start()

        # 获取 AI 发现的源列表
        from handler.sourceHandler import SourceLoader
        ai_sources = SourceLoader().get_ai_sources()

        return {
            "code": 1,
            "msg": "AI 搜索完成，代理验证已在后台进行",
            "proxies_found": len(proxies),
            "proxies_to_validate": queue_size,
            "sources_added": [{"name": s.name, "url": s.url, "description": s.description}
                              for s in ai_sources],
        }
    except Exception as e:
        return {"code": 0, "msg": str(e)}


# ===================== Proxy List & Test API =====================

@app.route('/api/proxies/list/')
def apiProxiesList():
    """代理列表，支持分页和排序"""
    proxies = proxy_handler.getAll()
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("size", 50, type=int)
    sort_by = request.args.get("sort", "speed")
    sort_order = request.args.get("sort_order", "asc")
    https_filter = request.args.get("https", "")

    # 过滤
    if https_filter == "1":
        proxies = [p for p in proxies if p.https]
    elif https_filter == "0":
        proxies = [p for p in proxies if not p.https]

    # 排序
    reverse = (sort_order == "desc")
    if sort_by == "speed":
        proxies.sort(key=lambda p: p.speed if p.speed and p.speed > 0 else 999, reverse=reverse)
    elif sort_by == "check_count":
        proxies.sort(key=lambda p: p.check_count or 0, reverse=reverse)
    elif sort_by == "use_count":
        proxies.sort(key=lambda p: p.use_count or 0, reverse=reverse)
    else:
        proxies.sort(key=lambda p: p.last_time or "", reverse=reverse)

    total = len(proxies)
    start = (page - 1) * page_size
    end = start + page_size
    page_proxies = proxies[start:end]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "proxies": [p.to_dict for p in page_proxies],
    }


@app.route('/api/proxy/test/', methods=['POST'])
def apiProxyTest():
    """通过指定代理获取目标URL内容"""
    data = request.get_json(force=True) if request.is_json else {}
    target_url = data.get("url", "https://ipaddress.my/zh_cn/")
    proxy_str = data.get("proxy", "")

    # 如果没有指定代理，随机选一个
    if not proxy_str:
        proxy_obj = proxy_handler.get()
        if not proxy_obj:
            return {"code": 0, "msg": "代理池为空，无可用代理"}
        proxy_str = proxy_obj.proxy
        proxy_handler.incrementUseCount(proxy_obj)

    try:
        import requests as _req
        proxies = {
            "http": f"http://{proxy_str}",
            "https": f"http://{proxy_str}",
        }
        # connect timeout 5s, read timeout 10s — 避免阻塞 gunicorn worker 过久
        start = _time.time()
        resp = _req.get(target_url, proxies=proxies, timeout=(5, 10),
                        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                        verify=False, allow_redirects=True)
        elapsed = round(_time.time() - start, 2)

        # 提取页面中的IP信息
        import re as _re
        ip_matches = _re.findall(r'(?:\d{1,3}\.){3}\d{1,3}', resp.text)
        detected_ips = list(set(ip_matches))[:5]

        # 限制返回内容大小，避免大响应阻塞网络传输
        content = resp.text[:200000]

        return {
            "code": 1,
            "proxy_used": proxy_str,
            "target_url": target_url,
            "status_code": resp.status_code,
            "elapsed": elapsed,
            "content": content,
            "detected_ips": detected_ips,
        }
    except _req.Timeout:
        return {"code": 0, "msg": f"代理 {proxy_str} 连接超时"}
    except _req.ConnectionError:
        return {"code": 0, "msg": f"代理 {proxy_str} 连接被拒绝或断开"}
    except _req.ChunkedEncodingError:
        return {"code": 0, "msg": f"代理 {proxy_str} 传输中断（连接被意外关闭）"}
    except Exception as e:
        err_msg = str(e)
        if 'closed unexpectedly' in err_msg.lower() or 'connection aborted' in err_msg.lower():
            return {"code": 0, "msg": f"代理 {proxy_str} 连接意外关闭"}
        return {"code": 0, "msg": f"请求失败: {err_msg}"}


def runFlask():
    if platform.system() == "Windows":
        app.run(host=conf.serverHost, port=conf.serverPort)
    else:
        import gunicorn.app.base

        class StandaloneApplication(gunicorn.app.base.BaseApplication):

            def __init__(self, app, options=None):
                self.options = options or {}
                self.application = app
                super(StandaloneApplication, self).__init__()

            def load_config(self):
                _config = dict([(key, value) for key, value in iteritems(self.options)
                                if key in self.cfg.settings and value is not None])
                for key, value in iteritems(_config):
                    self.cfg.set(key.lower(), value)

            def load(self):
                return self.application

        _options = {
            'bind': '%s:%s' % (conf.serverHost, conf.serverPort),
            'workers': 6,
            'timeout': 120,
            'graceful_timeout': 30,
            'max_requests': 1000,
            'max_requests_jitter': 50,
            'accesslog': '-',  # log to stdout
            'access_log_format': '%(h)s %(l)s %(t)s "%(r)s" %(s)s "%(a)s"'
        }
        StandaloneApplication(app, _options).run()


if __name__ == '__main__':
    runFlask()
