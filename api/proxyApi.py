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
    """ 手动触发代理池刷新 """
    try:
        refresh_handler = RefreshHandler()
        refresh_handler.refresh()
        return {"code": 1, "msg": "refresh triggered"}
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
            Checker("raw", proxy_queue)
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
            'workers': 4,
            'timeout': 300,
            'accesslog': '-',  # log to stdout
            'access_log_format': '%(h)s %(l)s %(t)s "%(r)s" %(s)s "%(a)s"'
        }
        StandaloneApplication(app, _options).run()


if __name__ == '__main__':
    runFlask()
