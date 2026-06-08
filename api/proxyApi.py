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
from werkzeug.wrappers import Response
from flask import Flask, jsonify, request

from util.six import iteritems
from helper.proxy import Proxy
from handler.proxyHandler import ProxyHandler
from handler.configHandler import ConfigHandler
from handler.refreshHandler import RefreshHandler

app = Flask(__name__)
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
    return {'url': api_list}


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
            'accesslog': '-',  # log to stdout
            'access_log_format': '%(h)s %(l)s %(t)s "%(r)s" %(s)s "%(a)s"'
        }
        StandaloneApplication(app, _options).run()


if __name__ == '__main__':
    runFlask()
