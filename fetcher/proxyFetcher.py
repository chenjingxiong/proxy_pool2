# -*- coding: utf-8 -*-
"""
-------------------------------------------------
   File Name：     proxyFetcher
   Description :
   Author :        JHao
   date：          2016/11/25
-------------------------------------------------
   Change Activity:
                   2016/11/25: proxyFetcher
-------------------------------------------------
"""
__author__ = 'JHao'

import re
import json
from time import sleep

from util.webRequest import WebRequest


class ProxyFetcher(object):
    """
    proxy getter
    """

    @staticmethod
    def freeProxy03():
        """ 开心代理 """
        target_urls = ["http://www.kxdaili.com/dailiip.html", "http://www.kxdaili.com/dailiip/2/1.html"]
        for url in target_urls:
            tree = WebRequest().get(url).tree
            for tr in tree.xpath("//table[@class='active']//tr")[1:]:
                ip = "".join(tr.xpath('./td[1]/text()')).strip()
                port = "".join(tr.xpath('./td[2]/text()')).strip()
                yield "%s:%s" % (ip, port)

    @staticmethod
    def freeProxy05(page_count=1):
        """ 快代理 https://www.kuaidaili.com """
        url_pattern = [
            'https://www.kuaidaili.com/free/inha/{}/',
            'https://www.kuaidaili.com/free/intr/{}/'
        ]
        url_list = []
        for page_index in range(1, page_count + 1):
            for pattern in url_pattern:
                url_list.append(pattern.format(page_index))

        for url in url_list:
            tree = WebRequest().get(url).tree
            proxy_list = tree.xpath('.//table//tr')
            sleep(1)  # 必须sleep 不然第二条请求不到数据
            for tr in proxy_list[1:]:
                yield ':'.join(tr.xpath('./td/text()')[0:2])

    @staticmethod
    def freeProxy07():
        """ 云代理 """
        urls = ['http://www.ip3366.net/free/?stype=1', "http://www.ip3366.net/free/?stype=2"]
        for url in urls:
            r = WebRequest().get(url, timeout=10)
            proxies = re.findall(r'<td>(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})</td>[\s\S]*?<td>(\d+)</td>', r.text)
            for proxy in proxies:
                yield ":".join(proxy)

    @staticmethod
    def freeProxy10():
        """ 89免费代理 """
        r = WebRequest().get("https://www.89ip.cn/index_1.html", timeout=10)
        proxies = re.findall(
            r'<td.*?>[\s\S]*?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})[\s\S]*?</td>[\s\S]*?<td.*?>[\s\S]*?(\d+)[\s\S]*?</td>',
            r.text)
        for proxy in proxies:
            yield ':'.join(proxy)

    @staticmethod
    def freeProxy11():
        """ 稻壳代理 https://www.docip.net/ """
        r = WebRequest().get("https://www.docip.net/data/free.json", timeout=10)
        try:
            for each in r.json['data']:
                yield each['ip']
        except Exception as e:
            print(e)

    # @staticmethod
    # def wallProxy01():
    #     """
    #     PzzQz https://pzzqz.com/
    #     """
    #     from requests import Session
    #     from lxml import etree
    #     session = Session()
    #     try:
    #         index_resp = session.get("https://pzzqz.com/", timeout=20, verify=False).text
    #         x_csrf_token = re.findall('X-CSRFToken": "(.*?)"', index_resp)
    #         if x_csrf_token:
    #             data = {"http": "on", "ping": "3000", "country": "cn", "ports": ""}
    #             proxy_resp = session.post("https://pzzqz.com/", verify=False,
    #                                       headers={"X-CSRFToken": x_csrf_token[0]}, json=data).json()
    #             tree = etree.HTML(proxy_resp["proxy_html"])
    #             for tr in tree.xpath("//tr"):
    #                 ip = "".join(tr.xpath("./td[1]/text()"))
    #                 port = "".join(tr.xpath("./td[2]/text()"))
    #                 yield "%s:%s" % (ip, port)
    #     except Exception as e:
    #         print(e)

    # @staticmethod
    # def freeProxy10():
    #     """
    #     墙外网站 cn-proxy
    #     :return:
    #     """
    #     urls = ['http://cn-proxy.com/', 'http://cn-proxy.com/archives/218']
    #     request = WebRequest()
    #     for url in urls:
    #         r = request.get(url, timeout=10)
    #         proxies = re.findall(r'<td>(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})</td>[\w\W]<td>(\d+)</td>', r.text)
    #         for proxy in proxies:
    #             yield ':'.join(proxy)

    # @staticmethod
    # def freeProxy11():
    #     """
    #     https://proxy-list.org/english/index.php
    #     :return:
    #     """
    #     urls = ['https://proxy-list.org/english/index.php?p=%s' % n for n in range(1, 10)]
    #     request = WebRequest()
    #     import base64
    #     for url in urls:
    #         r = request.get(url, timeout=10)
    #         proxies = re.findall(r"Proxy\('(.*?)'\)", r.text)
    #         for proxy in proxies:
    #             yield base64.b64decode(proxy).decode()

    # @staticmethod
    # def freeProxy12():
    #     urls = ['https://list.proxylistplus.com/Fresh-HTTP-Proxy-List-1']
    #     request = WebRequest()
    #     for url in urls:
    #         r = request.get(url, timeout=10)
    #         proxies = re.findall(r'<td>(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})</td>[\s\S]*?<td>(\d+)</td>', r.text)
    #         for proxy in proxies:
    #             yield ':'.join(proxy)

    @staticmethod
    def freeProxyScdn():
        """
        SCDN代理池 https://proxy.scdn.io/
        提供API接口获取代理
        """
        import requests

        # 方式1: 使用API获取（每次最多20个）
        api_url = "https://proxy.scdn.io/api/get_proxy.php?protocol=http&count=20"
        try:
            resp = requests.get(api_url, timeout=15, verify=False)
            data = resp.json()
            if data.get('code') == 200:
                proxies = data.get('data', {}).get('proxies', [])
                for proxy in proxies:
                    yield proxy
        except Exception as e:
            pass

        # 方式2: 从text页面获取更多代理
        text_url = "https://proxy.scdn.io/text.php"
        try:
            resp = requests.get(text_url, timeout=30, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line:
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy12():
        """ Proxifly GitHub代理列表 """
        import requests
        url = "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/http/data.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line:
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy13():
        """ JetKai GitHub代理列表 - HTTP """
        import requests
        url = "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy15():
        """ Seladb GitHub代理列表 """
        import requests
        url = "https://raw.githubusercontent.com/seladb/ProxyList/master/http.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line:
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy17():
        """ Monosans GitHub代理列表 """
        import requests
        url = "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line:
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy18():
        """ ClarkeTM GitHub代理列表 """
        import requests
        url = "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line:
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy43():
        """ Zevtyardt GitHub代理列表 """
        import requests
        url = "https://raw.githubusercontent.com/zevtyardt/proxy-list/main/http.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line:
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy46():
        """ Mmpx12 GitHub代理列表 """
        import requests
        url = "https://raw.githubusercontent.com/mmpx12/Proxy-List/master/proxies.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line:
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy47():
        """ OpenProxyList API """
        import requests
        url = "https://openproxylist.com/list.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line:
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy50():
        """ Proxifly HTTPS代理 """
        import requests
        url = "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/https/data.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line:
                    yield line
        except Exception as e:
            pass


    @staticmethod
    def freeProxy51():
        """ gitrecon1455/fresh-proxy-list (proxylist.txt) """
        import requests
        url = "https://raw.githubusercontent.com/gitrecon1455/fresh-proxy-list/main/proxylist.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy52():
        """ SevenworksDev/proxy-list (proxies/http.txt) """
        import requests
        url = "https://raw.githubusercontent.com/SevenworksDev/proxy-list/main/proxies/http.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy53():
        """ mzyui/proxy-list (http.txt) """
        import requests
        url = "https://raw.githubusercontent.com/mzyui/proxy-list/main/http.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy54():
        """ SevenworksDev/proxy-list (proxies/https.txt) """
        import requests
        url = "https://raw.githubusercontent.com/SevenworksDev/proxy-list/main/proxies/https.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy55():
        """ r00tee/Proxy-List (Https.txt) """
        import requests
        url = "https://raw.githubusercontent.com/r00tee/Proxy-List/main/Https.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy56():
        """ Argh94/Proxy-List (HTTP.txt) """
        import requests
        url = "https://raw.githubusercontent.com/Argh94/Proxy-List/main/HTTP.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy57():
        """ proxyscrape.com-https - proxyscrape API """
        import requests
        url = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=https&timeout=10000&country=all"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy58():
        """ Argh94/Proxy-List (All_Config.txt) """
        import requests
        url = "https://raw.githubusercontent.com/Argh94/Proxy-List/main/All_Config.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy59():
        """ Argh94/Proxy-List (Trojan.txt) """
        import requests
        url = "https://raw.githubusercontent.com/Argh94/Proxy-List/main/Trojan.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy60():
        """ Vann-Dev/proxy-list (proxies/http.txt) """
        import requests
        url = "https://raw.githubusercontent.com/Vann-Dev/proxy-list/main/proxies/http.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy61():
        """ SevenworksDev/proxy-list (proxies/unknown.txt) """
        import requests
        url = "https://raw.githubusercontent.com/SevenworksDev/proxy-list/main/proxies/unknown.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy62():
        """ vakhov/fresh-proxy-list (http.txt) """
        import requests
        url = "https://raw.githubusercontent.com/vakhov/fresh-proxy-list/master/http.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy63():
        """ proxyscrape.com-http - proxyscrape API """
        import requests
        url = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy64():
        """ MrMarble/proxy-list (all.txt) """
        import requests
        url = "https://raw.githubusercontent.com/MrMarble/proxy-list/main/all.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy65():
        """ databay-labs/free-proxy-list (http.txt) """
        import requests
        url = "https://raw.githubusercontent.com/databay-labs/free-proxy-list/master/http.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy66():
        """ themiralay/Proxy-List-World (data.txt) """
        import requests
        url = "https://raw.githubusercontent.com/themiralay/Proxy-List-World/master/data.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy67():
        """ Vann-Dev/proxy-list (proxies/https.txt) """
        import requests
        url = "https://raw.githubusercontent.com/Vann-Dev/proxy-list/main/proxies/https.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy68():
        """ roosterkid/openproxylist (V2RAY.txt) """
        import requests
        url = "https://raw.githubusercontent.com/roosterkid/openproxylist/main/V2RAY.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy69():
        """ prxchk/proxy-list (http.txt) """
        import requests
        url = "https://raw.githubusercontent.com/prxchk/proxy-list/main/http.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy70():
        """ MrMarble/proxy-list (country/.txt) """
        import requests
        url = "https://raw.githubusercontent.com/MrMarble/proxy-list/main/country/.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy71():
        """ roosterkid/openproxylist (HTTPS.txt) """
        import requests
        url = "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy72():
        """ ShiftyTR/Proxy-List (http.txt) """
        import requests
        url = "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy73():
        """ watchttvv/free-proxy-list (proxy.txt) """
        import requests
        url = "https://raw.githubusercontent.com/watchttvv/free-proxy-list/main/proxy.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy74():
        """ ShiftyTR/Proxy-List (https.txt) """
        import requests
        url = "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/https.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy75():
        """ vakhov/fresh-proxy-list (https.txt) """
        import requests
        url = "https://raw.githubusercontent.com/vakhov/fresh-proxy-list/master/https.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy76():
        """ a2u/free-proxy-list (free-proxy-list.txt) """
        import requests
        url = "https://raw.githubusercontent.com/a2u/free-proxy-list/master/free-proxy-list.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy77():
        """ TheSpeedX/PROXY-List HTTP """
        import requests
        url = "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy78():
        """ TheSpeedX/SOCKS-List SOCKS5 """
        import requests
        url = "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy79():
        """ TheSpeedX/SOCKS-List SOCKS4 """
        import requests
        url = "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks4.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy80():
        """ JetKai GitHub HTTPS代理列表 """
        import requests
        url = "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-https.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy81():
        """ JetKai GitHub SOCKS5代理列表 """
        import requests
        url = "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-socks5.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy82():
        """ ProxyScrape API v3 (all protocols) """
        import requests
        url = "https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&protocol=all&timeout=10000&country=all"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy83():
        """ ProxyScrape API v3 SOCKS5 """
        import requests
        url = "https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&protocol=socks5&timeout=10000&country=all"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy84():
        """ ProxyScrape API v3 SOCKS4 """
        import requests
        url = "https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&protocol=socks4&timeout=10000&country=all"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy85():
        """ Monosans GitHub SOCKS5代理列表 """
        import requests
        url = "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line:
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy86():
        """ Hookzof SOCKS5代理列表 """
        import requests
        url = "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line:
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy87():
        """ GeoNode API HTTP代理 """
        import requests
        url = "https://proxylist.geonode.com/api/proxy-list?protocols=http&limit=100&page=1&sort_by=lastChecked&sort_type=desc"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            import json
            data = json.loads(resp.text)
            for item in data.get('data', []):
                ip = item.get('ip', '')
                port = item.get('port', '')
                if ip and port:
                    yield f"{ip}:{port}"
        except Exception as e:
            pass

    @staticmethod
    def freeProxy88():
        """ rdavydov/Proxy-List HTTP """
        import requests
        url = "https://raw.githubusercontent.com/rdavydov/Proxy-List/master/proxies/http.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy89():
        """ rdavydov/Proxy-List SOCKS5 """
        import requests
        url = "https://raw.githubusercontent.com/rdavydov/Proxy-List/master/proxies/socks5.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy90():
        """ zevtyardt/proxy-list SOCKS4 """
        import requests
        url = "https://raw.githubusercontent.com/zevtyardt/proxy-list/main/socks4.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy91():
        """ zevtyardt/proxy-list SOCKS5 """
        import requests
        url = "https://raw.githubusercontent.com/zevtyardt/proxy-list/main/socks5.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy92():
        """ Proxifly SOCKS4代理列表 """
        import requests
        url = "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/socks4/data.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                for prefix in ['socks4://', 'socks5://', 'http://', 'https://']:
                    if line.startswith(prefix):
                        line = line[len(prefix):]
                        break
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy93():
        """ Proxifly SOCKS5代理列表 """
        import requests
        url = "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/socks5/data.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                for prefix in ['socks4://', 'socks5://', 'http://', 'https://']:
                    if line.startswith(prefix):
                        line = line[len(prefix):]
                        break
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy94():
        """ ProxyScrape API v2 SOCKS4 """
        import requests
        url = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks4&timeout=10000&country=all"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy95():
        """ ProxyScrape API v2 SOCKS5 """
        import requests
        url = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=10000&country=all"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy96():
        """ prxchk/proxy-list SOCKS5 """
        import requests
        url = "https://raw.githubusercontent.com/prxchk/proxy-list/main/socks5.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy97():
        """ GeoNode API SOCKS5代理 """
        import requests
        url = "https://proxylist.geonode.com/api/proxy-list?protocols=socks5&limit=100&page=1&sort_by=lastChecked&sort_type=desc"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            import json
            data = json.loads(resp.text)
            for item in data.get('data', []):
                ip = item.get('ip', '')
                port = item.get('port', '')
                if ip and port:
                    yield f"{ip}:{port}"
        except Exception as e:
            pass

    @staticmethod
    def freeProxy98():
        """ ShiftyTR/Proxy-List SOCKS4 """
        import requests
        url = "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks4.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy99():
        """ ShiftyTR/Proxy-List SOCKS5 """
        import requests
        url = "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks5.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy100():
        """ vakhov/fresh-proxy-list SOCKS4 """
        import requests
        url = "https://raw.githubusercontent.com/vakhov/fresh-proxy-list/master/socks4.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line and not line.startswith('#'):
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def aiProxySearch():
        """ AI智能代理搜索 """
        from helper.aiSearch import AISearch
        ai = AISearch()
        for proxy in ai.search_proxies():
            yield proxy


if __name__ == '__main__':
    p = ProxyFetcher()
    for _ in p.freeProxy03():
        print(_)

# http://nntime.com/proxy-list-01.htm
