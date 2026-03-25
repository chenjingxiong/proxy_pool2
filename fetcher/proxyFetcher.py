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
    def freeProxy01():
        """
        站大爷 https://www.zdaye.com/dayProxy.html
        """
        start_url = "https://www.zdaye.com/dayProxy.html"
        html_tree = WebRequest().get(start_url, verify=False).tree
        latest_page_time = html_tree.xpath("//span[@class='thread_time_info']/text()")[0].strip()
        from datetime import datetime
        interval = datetime.now() - datetime.strptime(latest_page_time, "%Y/%m/%d %H:%M:%S")
        if interval.seconds < 300:  # 只采集5分钟内的更新
            target_url = "https://www.zdaye.com/" + html_tree.xpath("//h3[@class='thread_title']/a/@href")[0].strip()
            while target_url:
                _tree = WebRequest().get(target_url, verify=False).tree
                for tr in _tree.xpath("//table//tr"):
                    ip = "".join(tr.xpath("./td[1]/text()")).strip()
                    port = "".join(tr.xpath("./td[2]/text()")).strip()
                    yield "%s:%s" % (ip, port)
                next_page = _tree.xpath("//div[@class='page']/a[@title='下一页']/@href")
                target_url = "https://www.zdaye.com/" + next_page[0].strip() if next_page else False
                sleep(5)

    @staticmethod
    def freeProxy02():
        """
        代理66 http://www.66ip.cn/
        """
        url = "http://www.66ip.cn/"
        resp = WebRequest().get(url, timeout=10).tree
        for i, tr in enumerate(resp.xpath("(//table)[3]//tr")):
            if i > 0:
                ip = "".join(tr.xpath("./td[1]/text()")).strip()
                port = "".join(tr.xpath("./td[2]/text()")).strip()
                yield "%s:%s" % (ip, port)

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
    def freeProxy04():
        """ FreeProxyList https://www.freeproxylists.net/zh/ """
        url = "https://www.freeproxylists.net/zh/?c=CN&pt=&pr=&a%5B%5D=0&a%5B%5D=1&a%5B%5D=2&u=50"
        tree = WebRequest().get(url, verify=False).tree
        from urllib import parse

        def parse_ip(input_str):
            html_str = parse.unquote(input_str)
            ips = re.findall(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', html_str)
            return ips[0] if ips else None

        for tr in tree.xpath("//tr[@class='Odd']") + tree.xpath("//tr[@class='Even']"):
            ip = parse_ip("".join(tr.xpath('./td[1]/script/text()')).strip())
            port = "".join(tr.xpath('./td[2]/text()')).strip()
            if ip:
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
    def freeProxy06():
        """ 冰凌代理 https://www.binglx.cn """
        url = "https://www.binglx.cn/?page=1"
        try:
            tree = WebRequest().get(url).tree
            proxy_list = tree.xpath('.//table//tr')
            for tr in proxy_list[1:]:
                yield ':'.join(tr.xpath('./td/text()')[0:2])
        except Exception as e:
            print(e)

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
    def freeProxy08():
        """ 小幻代理 """
        urls = ['https://ip.ihuan.me/address/5Lit5Zu9.html']
        for url in urls:
            r = WebRequest().get(url, timeout=10)
            proxies = re.findall(r'>\s*?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s*?</a></td><td>(\d+)</td>', r.text)
            for proxy in proxies:
                yield ":".join(proxy)

    @staticmethod
    def freeProxy09(page_count=1):
        """ 免费代理库 """
        for i in range(1, page_count + 1):
            url = 'http://ip.jiangxianli.com/?country=中国&page={}'.format(i)
            html_tree = WebRequest().get(url, verify=False).tree
            for index, tr in enumerate(html_tree.xpath("//table//tr")):
                if index == 0:
                    continue
                yield ":".join(tr.xpath("./td/text()")[0:2]).strip()

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
    def freeProxy14():
        """ ProxyScrape API """
        import requests
        url = "https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line:
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
    def freeProxy16():
        """ TheSpeedX PROXIER """
        import requests
        url = "https://raw.githubusercontent.com/TheSpeedX/PROXIER/master/proxier.txt"
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
    def freeProxy19():
        """ GfpCom GitHub代理列表 """
        import requests
        url = "https://raw.githubusercontent.com/gfpcom/free-proxy-list/main/http.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line:
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy20():
        """ Fate0 GitHub代理列表 """
        import requests
        url = "https://raw.githubusercontent.com/fate0/proxylist/master/proxy_list.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line:
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy21():
        """ TopChina GitHub代理列表 """
        import requests
        url = "https://raw.githubusercontent.com/TopChina/proxy-list/master/http.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line:
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy22():
        """ Databay Labs GitHub代理列表 """
        import requests
        url = "https://raw.githubusercontent.com/databay-labs/free-proxy-list/main/http.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line:
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy23():
        """ Casa-LS GitHub代理列表 """
        import requests
        url = "https://raw.githubusercontent.com/casa-ls/proxy-list/main/http.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line:
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy24():
        """ Iplocate GitHub代理列表 """
        import requests
        url = "https://raw.githubusercontent.com/iplocate/free-proxy-list/main/http.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line:
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy25():
        """ LeChann GitHub代理列表 """
        import requests
        url = "https://raw.githubusercontent.com/LeChann/ProxyList/main/http.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line:
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy26():
        """ Rdavydov GitHub代理列表 """
        import requests
        url = "https://raw.githubusercontent.com/rdavydov/proxy-list/main/http.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line:
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy27():
        """ Mertguvencli GitHub代理列表 """
        import requests
        url = "https://raw.githubusercontent.com/mertguvencli/free-proxy-list/main/http-proxies.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line:
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy28():
        """ Zaeem20 GitHub代理列表 """
        import requests
        url = "https://raw.githubusercontent.com/Zaeem20/FREE_PROXIES_LIST/main/http_proxies.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line:
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy29():
        """ R00tee GitHub代理列表 """
        import requests
        url = "https://raw.githubusercontent.com/r00tee/Proxy-List/master/http.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line:
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy30():
        """ MrMarble GitHub代理列表 """
        import requests
        url = "https://raw.githubusercontent.com/MrMarble/proxy-list/master/https.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line:
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy31():
        """ Fyvri GitHub代理列表 """
        import requests
        url = "https://raw.githubusercontent.com/fyvri/fresh-proxy-list/main/http.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line:
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy32():
        """ Anonym0usWork1221 GitHub代理列表 - HTTP """
        import requests
        url = "https://raw.githubusercontent.com/Anonym0usWork1221/Free-Proxies/main/http.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line:
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy33():
        """ ProbiusOfficial GitHub代理列表 """
        import requests
        url = "https://raw.githubusercontent.com/ProbiusOfficial/Free-Proxy-List/main/http.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line:
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy34():
        """ V2era GitHub代理列表 """
        import requests
        url = "https://raw.githubusercontent.com/v2era/Proxy-List/master/http.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line:
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy35():
        """ S4wfit GitHub代理列表 """
        import requests
        url = "https://raw.githubusercontent.com/s4wfit/Proxy-List/main/http.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line:
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy36():
        """ Watchttvv GitHub代理列表 """
        import requests
        url = "https://raw.githubusercontent.com/watchttvv/free-proxy-list/main/proxy_list.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line:
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy37():
        """ Roosterkid GitHub代理列表 """
        import requests
        url = "https://raw.githubusercontent.com/roosterkid/openproxylist/main/proxies.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line:
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy38():
        """ Shjalayeri GitHub代理列表 """
        import requests
        url = "https://raw.githubusercontent.com/shjalayeri/proxy-list/main/proxy_list.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line:
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy39():
        """ ALIILAPRO GitHub代理列表 """
        import requests
        url = "https://raw.githubusercontent.com/ALIILAPRO/Proxy-List/master/proxy.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line:
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy40():
        """ Officialpiyush GitHub代理列表 """
        import requests
        url = "https://raw.githubusercontent.com/officialpiyush/Proxy-List/main/https.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line:
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy41():
        """ Abovlms GitHub代理列表 """
        import requests
        url = "https://raw.githubusercontent.com/abovlms/proxylist/main/proxy_list.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line:
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy42():
        """ Hidesslayer GitHub代理列表 """
        import requests
        url = "https://raw.githubusercontent.com/hidesslayer/proxy-list/main/http.txt"
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
    def freeProxy44():
        """ Ethereum-ex GitHub代理列表 """
        import requests
        url = "https://raw.githubusercontent.com/ethereum-ex/proxy-list/master/http.txt"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line:
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy45():
        """ Wklchris GitHub代理列表 """
        import requests
        url = "https://raw.githubusercontent.com/wklchris/Proxy-List/master/proxy_list.txt"
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
    def freeProxy48():
        """ ProxyScrape SOCKS4 """
        import requests
        url = "https://api.proxyscrape.com/v2/?request=get&protocol=socks4&timeout=10000&country=all&ssl=all&anonymity=all"
        try:
            resp = requests.get(url, timeout=20, verify=False)
            for line in resp.text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line:
                    yield line
        except Exception as e:
            pass

    @staticmethod
    def freeProxy49():
        """ ProxyScrape SOCKS5 """
        import requests
        url = "https://api.proxyscrape.com/v2/?request=get&protocol=socks5&timeout=10000&country=all&ssl=all&anonymity=all"
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


if __name__ == '__main__':
    p = ProxyFetcher()
    for _ in p.freeProxy06():
        print(_)

# http://nntime.com/proxy-list-01.htm
