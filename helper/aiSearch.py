# -*- coding: utf-8 -*-
"""
-------------------------------------------------
   File Name：     aiSearch
   Description :   AI智能代理搜索，调用LLM发现代理源并提取代理
   Author :        proxy_pool
   date：          2024/6/8
-------------------------------------------------
"""
import re
import json
import requests
from handler.configHandler import ConfigHandler
from handler.logHandler import LogHandler


class AISearch(object):
    """AI-powered proxy source discovery and proxy extraction"""

    def __init__(self):
        self.conf = ConfigHandler()
        self.log = LogHandler("ai_search")
        self.api_key = self.conf.aiApiKey
        self.base_url = self.conf.aiApiBaseUrl.rstrip("/")
        self.model = self.conf.aiModel
        self.timeout = self.conf.aiApiTimeout
        self.max_sources = self.conf.aiMaxSources

    @property
    def enabled(self):
        return bool(self.api_key)

    def _call_llm(self, system_prompt, user_prompt):
        """调用 OpenAI 兼容 API"""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 2048,
        }
        try:
            resp = requests.post(url, headers=headers, json=payload,
                                 timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            self.log.error(f"LLM API call failed: {e}")
            return ""

    def _parse_json_array(self, text):
        """从文本中提取 JSON 数组"""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\[.*\]", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
        return []

    def discover_proxy_sources(self):
        """让 AI 推荐代理源 URL"""
        self.log.info("AI: discovering proxy sources...")
        system_prompt = (
            "You are a proxy source discovery assistant. "
            "Return ONLY a valid JSON array of URL strings. "
            "Each URL must point to a website or GitHub repository that "
            "currently publishes free HTTP/HTTPS proxy lists. "
            "Include only URLs that are likely to be active and accessible now. "
            f"Return at most {self.max_sources} URLs."
        )
        user_prompt = (
            "Find websites, APIs, and GitHub repositories that currently publish "
            "free HTTP/HTTPS proxy lists (ip:port format). Focus on sources that are "
            "updated frequently. Return the URLs as a JSON array."
        )
        response = self._call_llm(system_prompt, user_prompt)
        urls = self._parse_json_array(response)
        if urls and isinstance(urls, list):
            valid_urls = [u for u in urls if isinstance(u, str) and u.startswith("http")]
            self.log.info(f"AI: discovered {len(valid_urls)} proxy source URLs")
            return valid_urls[:self.max_sources]

        # 回退：从文本中提取 URL
        url_pattern = re.compile(r"https?://[^\s,\"']+")
        fallback = list(set(url_pattern.findall(response)))[:self.max_sources]
        self.log.info(f"AI: fallback URL extraction found {len(fallback)} URLs")
        return fallback

    def extract_proxies_from_url(self, url):
        """抓取网页并用 AI 提取代理地址"""
        self.log.info(f"AI: extracting proxies from {url}")
        try:
            resp = requests.get(url, timeout=self.timeout, verify=False,
                                headers={"User-Agent": "Mozilla/5.0"})
            content = resp.text[:8000]
        except Exception as e:
            self.log.warning(f"AI: failed to fetch {url}: {e}")
            return []

        system_prompt = (
            "You are a proxy address extractor. Given webpage content, extract "
            "all proxy addresses in ip:port format. Return ONLY a JSON array of "
            'strings like ["1.2.3.4:8080", "5.6.7.8:3128"]. '
            "If no proxies found, return []."
        )
        user_prompt = f"Extract all proxy addresses from:\n{content}"

        response = self._call_llm(system_prompt, user_prompt)
        proxies = self._parse_json_array(response)
        if proxies and isinstance(proxies, list):
            return [str(p) for p in proxies if isinstance(p, str) and ":" in p]

        # 回退：正则提取
        ip_pattern = re.compile(
            r"(?:\d{1,3}\.){3}\d{1,3}:\d{2,5}"
        )
        fallback = list(set(ip_pattern.findall(content)))
        return fallback

    def search_proxies(self):
        """主流程：发现源 → 提取代理 → 去重"""
        if not self.enabled:
            self.log.info("AI search disabled (no API key configured)")
            return []

        all_proxies = set()
        try:
            sources = self.discover_proxy_sources()
            for url in sources:
                try:
                    proxies = self.extract_proxies_from_url(url)
                    all_proxies.update(proxies)
                    self.log.info(
                        f"AI: {url[:50]}... -> {len(proxies)} proxies"
                    )
                except Exception as e:
                    self.log.warning(f"AI: error processing {url}: {e}")
                    continue
        except Exception as e:
            self.log.error(f"AI: search_proxies failed: {e}")
            return []

        self.log.info(
            f"AI: search complete - {len(all_proxies)} unique proxies found"
        )
        return list(all_proxies)
