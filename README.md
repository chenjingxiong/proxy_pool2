
ProxyPool 爬虫代理IP池
=======
[![Build Status](https://travis-ci.org/jhao104/proxy_pool.svg?branch=master)](https://travis-ci.org/jhao104/proxy_pool)
[![](https://img.shields.io/badge/Powered%20by-@j_hao104-green.svg)](http://www.spiderpy.cn/blog/)
[![Packagist](https://img.shields.io/packagist/l/doctrine/orm.svg)](https://github.com/jhao104/proxy_pool/blob/master/LICENSE)
[![GitHub contributors](https://img.shields.io/github/contributors/jhao104/proxy_pool.svg)](https://github.com/jhao104/proxy_pool/graphs/contributors)
[![](https://img.shields.io/badge/language-Python-green.svg)](https://github.com/jhao104/proxy_pool)

    ______                        ______             _
    | ___ \_                      | ___ \           | |
    | |_/ / \__ __   __  _ __   _ | |_/ /___   ___  | |
    |  __/|  _// _ \ \ \/ /| | | ||  __// _ \ / _ \ | |
    | |   | | | (_) | >  < \ |_| || |  | (_) | (_) || |___
    \_|   |_|  \___/ /_/\_\ \__  |\_|   \___/ \___/ \_____\
                           __ / /
                          /___ /

### ProxyPool

爬虫代理IP池项目,主要功能为定时采集网上发布的免费代理验证入库，定时验证入库的代理保证代理的可用性，提供API和CLI两种使用方式，同时提供**虚拟代理服务器**让外部应用无需改代码即可无感使用代理池。你也可以扩展代理源以增加代理池IP的质量和数量。

* 文档: [document](https://proxy-pool.readthedocs.io/zh/latest/) [![Documentation Status](https://readthedocs.org/projects/proxy-pool/badge/?version=latest)](https://proxy-pool.readthedocs.io/zh/latest/?badge=latest)

* 支持版本: [![](https://img.shields.io/badge/Python-2.7-green.svg)](https://docs.python.org/2.7/)
[![](https://img.shields.io/badge/Python-3.5-blue.svg)](https://docs.python.org/3.5/)
[![](https://img.shields.io/badge/Python-3.6-blue.svg)](https://docs.python.org/3.6/)
[![](https://img.shields.io/badge/Python-3.7-blue.svg)](https://docs.python.org/3.7/)
[![](https://img.shields.io/badge/Python-3.8-blue.svg)](https://docs.python.org/3.8/)
[![](https://img.shields.io/badge/Python-3.9-blue.svg)](https://docs.python.org/3.9/)
[![](https://img.shields.io/badge/Python-3.10-blue.svg)](https://docs.python.org/3.10/)
[![](https://img.shields.io/badge/Python-3.11-blue.svg)](https://docs.python.org/3.11/)

* 测试地址: http://demo.spiderpy.cn (勿压谢谢)

* 付费代理推荐: [luminati-china](https://get.brightdata.com/github_jh). 国外的亮数据BrightData（以前叫luminati）被认为是代理市场领导者，覆盖全球的7200万IP，大部分是真人住宅IP，成功率扛扛的。付费套餐多种，需要高质量代理IP的可以注册后联系中文客服。[申请免费试用](https://get.brightdata.com/github_jh) 目前有50%折扣优惠活动。(PS:用不明白的同学可以参考这个[使用教程](https://www.cnblogs.com/jhao/p/15611785.html))。


### 运行项目

##### 下载代码:

* git clone

```bash
git clone git@github.com:jhao104/proxy_pool.git
```

* releases

```bash
https://github.com/jhao104/proxy_pool/releases 下载对应zip文件
```

##### 安装依赖:

```bash
pip install -r requirements.txt
```

##### 更新配置:


```python
# setting.py 为项目配置文件

# 配置API服务

HOST = "0.0.0.0"               # IP
PORT = 5000                    # 监听端口


# 配置数据库

DB_CONN = 'redis://:pwd@127.0.0.1:8888/0'


# 配置 ProxyFetcher

PROXY_FETCHER = [
    "freeProxy01",      # 这里是启用的代理抓取方法名，所有fetch方法位于fetcher/proxyFetcher.py
    "freeProxy02",
    # ....
]
```

#### 启动项目:

```bash
# 如果已经具备运行条件, 可用通过proxyPool.py启动。
# 程序分为: schedule 调度程序 和 server Api服务

# 启动调度程序
python proxyPool.py schedule

# 启动webApi服务
python proxyPool.py server

```

### Docker Image

```bash
docker pull jhao104/proxy_pool

docker run --env DB_CONN=redis://:password@ip:port/0 -p 5010:5010 jhao104/proxy_pool:latest
```
### docker-compose

项目目录下运行: 
``` bash
docker-compose up -d
```

`docker-compose.yml` 会启动 4 个容器：

| 服务 | 容器名 | 端口 | 说明 |
| --- | --- | --- | --- |
| redis | proxy_pool_redis | 6380 | 代理存储 |
| app | proxy_pool_app | 5010 | Web API + Dashboard |
| scheduler | proxy_pool_scheduler | — | 定时抓取 + 验证 |
| proxy_server | proxy_pool_server | **5011** | **虚拟代理服务器（新功能）** |

### 虚拟代理服务器（Virtual Proxy Server）

外部应用将代理池当作**单个** HTTP/HTTPS 代理使用，内部自动从池中随机挑选可用代理转发流量，**无需改业务代码**。

* 代码: [`proxyServer/virtualProxy.py`](proxyServer/virtualProxy.py)
* 默认端口: `5011`（通过环境变量 `VIRTUAL_PROXY_PORT` 配置）

##### 工作机制

1. 外部应用将 `http://<server>:5011` 设为 HTTP/HTTPS 代理
2. HTTP 请求直接透传到上游代理（携带绝对 URL）
3. HTTPS 请求通过 `CONNECT` 隧道穿透上游代理
4. 单次请求代理失败时自动重试换代理（默认 3 次）
5. 成功转发时累加代理的 `use_count`

##### 使用示例

```bash
# curl
curl -x http://192.168.9.8:5011 https://api.ipify.org -k
curl -x http://192.168.9.8:5011 http://myip.ipip.net

# Python requests
import requests
proxies = {
    "http":  "http://192.168.9.8:5011",
    "https": "http://192.168.9.8:5011",
}
r = requests.get("https://www.baidu.com", proxies=proxies, verify=False)
```

```bash
# 全局环境变量（一次性，影响所有命令行工具）
export http_proxy=http://192.168.9.8:5011
export https_proxy=http://192.168.9.8:5011
```

##### 可选环境变量

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `VIRTUAL_PROXY_HOST` | `0.0.0.0` | 监听地址 |
| `VIRTUAL_PROXY_PORT` | `5011` | 监听端口 |
| `VIRTUAL_PROXY_RETRIES` | `3` | 单请求代理失败重试次数 |
| `VIRTUAL_PROXY_AUDIT_FILE` | `logs/virtual_proxy_audit.log` | 审计日志文件路径 |
| `VIRTUAL_PROXY_AUDIT_SIZE_KB` | `1024` | 单个审计日志文件最大 KB，超出自动轮转 |
| `VIRTUAL_PROXY_AUDIT_BACKUP_COUNT` | `5` | 审计日志保留的历史份数 |

##### 审计日志

每次外部调用自动记录，JSON Lines 格式，存储于 `logs/virtual_proxy_audit.log`（docker-compose 挂载至宿主机 `./logs/`）。

日志字段：

| 字段 | 说明 |
| --- | --- |
| `ts` | 时间 `YYYY-MM-DD HH:MM:SS` |
| `client` | 调用方 IP:Port |
| `method` | 请求方法（GET / CONNECT 等） |
| `target` | 目标 URL（CONNECT 为 host:port） |
| `proxy` | 使用的代理 IP:Port |
| `success` | 是否成功（HTTP: 收到有效响应；CONNECT: 隧道建立） |
| `status` | HTTP 状态码（0 = 无有效响应，200/502/403 等） |
| `duration` | 耗时（秒） |
| `error` | 失败原因（仅失败时有） |

日志示例：
```json
{"ts":"2026-06-16 01:41:26","client":"192.168.9.11:54321","method":"GET","target":"http://myip.ipip.net/","proxy":"104.17.105.39:80","success":true,"status":200,"duration":0.309}
{"ts":"2026-06-16 01:42:21","client":"192.168.9.11:54322","method":"CONNECT","target":"api.ipify.org:443","proxy":"5.10.244.140:80","success":false,"status":502,"duration":6.239,"error":"upstream HTTP/1.1 400 Bad Request"}
```

### 使用

* Api

启动web服务后, 默认配置下会开启 http://127.0.0.1:5010 的api接口服务:

| api | method | Description | params|
| ----| ---- | ---- | ----|
| / | GET | api介绍 | None |
| /get | GET | 随机获取一个代理| 可选参数: `?type=https` 过滤支持https的代理|
| /pop | GET | 获取并删除一个代理| 可选参数: `?type=https` 过滤支持https的代理|
| /all | GET | 获取所有代理 |可选参数: `?type=https` 过滤支持https的代理|
| /count | GET | 查看代理数量 |None|
| /delete | GET | 删除代理  |`?proxy=host:ip`|


* 代理验证

验证器通过 GET 访问真实网站并校验响应内容，确保代理可真实传输网页内容（而非仅返回状态码）：

| 协议 | 验证目标 | 内容校验规则 |
| --- | --- | --- |
| HTTP | `http://www.baidu.com` | 响应含「百度」或「baidu」 |
| HTTP | `http://myip.ipip.net` | 响应含 IP 地址 + 「来自于」或「IP」 |
| HTTPS | `https://www.baidu.com` | 响应含「百度」或「baidu」 |
| HTTPS | `https://api.ipify.org` | 响应体整行为 IP 地址 |

**所有目标必须全部通过**才视为该协议可用（AND 逻辑）：任一目标超时、状态码非 200、返回空响应、Cloudflare 拦截页或内容不匹配，即视为不可用，不进入候选池。


* 爬虫使用

　　如果要在爬虫代码中使用的话， 可以将此api封装成函数直接使用，例如：

```python
import requests

def get_proxy():
    return requests.get("http://127.0.0.1:5010/get/").json()

def delete_proxy(proxy):
    requests.get("http://127.0.0.1:5010/delete/?proxy={}".format(proxy))

# your spider code

def getHtml():
    # ....
    retry_count = 5
    proxy = get_proxy().get("proxy")
    while retry_count > 0:
        try:
            html = requests.get('http://www.example.com', proxies={"http": "http://{}".format(proxy)})
            # 使用代理访问
            return html
        except Exception:
            retry_count -= 1
    # 删除代理池中代理
    delete_proxy(proxy)
    return None
```

### 扩展代理

　　项目默认包含几个免费的代理获取源，但是免费的毕竟质量有限，所以如果直接运行可能拿到的代理质量不理想。所以，提供了代理获取的扩展方法。

　　添加一个新的代理源方法如下:

* 1、首先在[ProxyFetcher](https://github.com/jhao104/proxy_pool/blob/1a3666283806a22ef287fba1a8efab7b94e94bac/fetcher/proxyFetcher.py#L21)类中添加自定义的获取代理的静态方法，
该方法需要以生成器(yield)形式返回`host:ip`格式的代理，例如:

```python

class ProxyFetcher(object):
    # ....

    # 自定义代理源获取方法
    @staticmethod
    def freeProxyCustom1():  # 命名不和已有重复即可

        # 通过某网站或者某接口或某数据库获取代理
        # 假设你已经拿到了一个代理列表
        proxies = ["x.x.x.x:3128", "x.x.x.x:80"]
        for proxy in proxies:
            yield proxy
        # 确保每个proxy都是 host:ip正确的格式返回
```

* 2、添加好方法后，修改[setting.py](https://github.com/jhao104/proxy_pool/blob/1a3666283806a22ef287fba1a8efab7b94e94bac/setting.py#L47)文件中的`PROXY_FETCHER`项：

　　在`PROXY_FETCHER`下添加自定义方法的名字:

```python
PROXY_FETCHER = [
    "freeProxy01",    
    "freeProxy02",
    # ....
    "freeProxyCustom1"  #  # 确保名字和你添加方法名字一致
]
```


　　`schedule` 进程会每隔一段时间抓取一次代理，下次抓取时会自动识别调用你定义的方法。

### 免费代理源

   目前实现的采集免费代理网站有(排名不分先后, 下面仅是对其发布的免费代理情况, 付费代理测评可以参考[这里](https://zhuanlan.zhihu.com/p/33576641)): 
   
  | 代理名称          |  状态  |  更新速度 |  可用率  |  地址 | 代码                                             |
  |---------------|  ---- | --------  | ------  | ----- |------------------------------------------------|
  | 66代理          |  ✔    |     ★     |   *     | [地址](http://www.66ip.cn/)         | [`freeProxy02`](/fetcher/proxyFetcher.py#L50)  |
  | 开心代理          |   ✔   |     ★     |   *     | [地址](http://www.kxdaili.com/)     | [`freeProxy03`](/fetcher/proxyFetcher.py#L63)  |
  | FreeProxyList |   ✔  |    ★     |   *    | [地址](https://www.freeproxylists.net/zh/) | [`freeProxy04`](/fetcher/proxyFetcher.py#L74)  |
  | 快代理           |  ✔    |     ★     |   *     | [地址](https://www.kuaidaili.com/)  | [`freeProxy05`](/fetcher/proxyFetcher.py#L92)  |
  | 冰凌代理          |  ✔    |    ★★★    |   *     | [地址](https://www.binglx.cn/) | [`freeProxy06`](/fetcher/proxyFetcher.py#L111) |
  | 云代理           |  ✔    |    ★     |   *     | [地址](http://www.ip3366.net/)      | [`freeProxy07`](/fetcher/proxyFetcher.py#L123) |
  | 小幻代理          |  ✔    |    ★★    |    *    | [地址](https://ip.ihuan.me/)        | [`freeProxy08`](/fetcher/proxyFetcher.py#L133) |
  | 免费代理库         |  ✔    |     ☆     |    *    | [地址](http://ip.jiangxianli.com/)   | [`freeProxy09`](/fetcher/proxyFetcher.py#L143) |
  | 89代理          |  ✔    |     ☆     |   *     | [地址](https://www.89ip.cn/)         | [`freeProxy10`](/fetcher/proxyFetcher.py#L154) |
  | 稻壳代理          |  ✔    |     ★★    |   ***   | [地址](https://www.docip.ne)         | [`freeProxy11`](/fetcher/proxyFetcher.py#L164) |

  
  如果还有其他好的免费代理网站, 可以在提交在[issues](https://github.com/jhao104/proxy_pool/issues/71), 下次更新时会考虑在项目中支持。

### 问题反馈

　　任何问题欢迎在[Issues](https://github.com/jhao104/proxy_pool/issues) 中反馈，同时也可以到我的[博客](http://www.spiderpy.cn/blog/message)中留言。

　　你的反馈会让此项目变得更加完美。

### 贡献代码

　　本项目仅作为基本的通用的代理池架构，不接收特有功能(当然,不限于特别好的idea)。

　　本项目依然不够完善，如果发现bug或有新的功能添加，请在[Issues](https://github.com/jhao104/proxy_pool/issues)中提交bug(或新功能)描述，我会尽力改进，使她更加完美。

　　这里感谢以下contributor的无私奉献：

　　[@kangnwh](https://github.com/kangnwh) | [@bobobo80](https://github.com/bobobo80) | [@halleywj](https://github.com/halleywj) | [@newlyedward](https://github.com/newlyedward) | [@wang-ye](https://github.com/wang-ye) | [@gladmo](https://github.com/gladmo) | [@bernieyangmh](https://github.com/bernieyangmh) | [@PythonYXY](https://github.com/PythonYXY) | [@zuijiawoniu](https://github.com/zuijiawoniu) | [@netAir](https://github.com/netAir) | [@scil](https://github.com/scil) | [@tangrela](https://github.com/tangrela) | [@highroom](https://github.com/highroom) | [@luocaodan](https://github.com/luocaodan) | [@vc5](https://github.com/vc5) | [@1again](https://github.com/1again) | [@obaiyan](https://github.com/obaiyan) | [@zsbh](https://github.com/zsbh) | [@jiannanya](https://github.com/jiannanya) | [@Jerry12228](https://github.com/Jerry12228)


### Release Notes

   [changelog](https://github.com/jhao104/proxy_pool/blob/master/docs/changelog.rst)

<a href="https://hellogithub.com/repository/92a066e658d147cc8bd8397a1cb88183" target="_blank"><img src="https://api.hellogithub.com/v1/widgets/recommend.svg?rid=92a066e658d147cc8bd8397a1cb88183&claim_uid=DR60NequsjP54Lc" alt="Featured｜HelloGitHub" style="width: 250px; height: 54px;" width="250" height="54" /></a>
