# -*- coding: utf-8 -*-
"""
   aiSearch - AI智能代理搜索，调用LLM发现代理源并提取代理
"""
import re
import json
import time
import requests
from handler.configHandler import ConfigHandler
from handler.logHandler import LogHandler


class AISearch(object):
    """AI-powered proxy source discovery and proxy extraction"""

    SEARCH_HARD_LIMIT = 120

    def __init__(self):
        self.conf = ConfigHandler()
        self.log = LogHandler("ai_search")
        self.api_key = self.conf.aiApiKey
        self.base_url = self.conf.aiApiBaseUrl.rstrip("/")
        self.model = self.conf.aiModel
        self.timeout = self.conf.aiApiTimeout
        self.max_sources = min(self.conf.aiMaxSources, 3)
        self._successful_sources = []  # 跟踪成功的源URL

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
                                 timeout=min(self.timeout, 60))
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except requests.Timeout:
            self.log.error("LLM API call timed out")
            return ""
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

    def _extract_proxies_regex(self, text):
        """正则提取代理地址"""
        ip_pattern = re.compile(r"(?:\d{1,3}\.){3}\d{1,3}:\d{2,5}")
        return list(set(ip_pattern.findall(text)))

    def _log_search_result(self, total_found, direct_count, source_count):
        """记录AI搜索结果到Redis"""
        try:
            from db.dbClient import DbClient
            db = DbClient(self.conf.dbConn)
            # 使用原生Redis连接写日志
            import redis
            conn = redis.Redis.from_url(self.conf.dbConn, decode_responses=True)
            log_entry = json.dumps({
                'time': time.strftime('%Y-%m-%d %H:%M:%S'),
                'total_found': total_found,
                'direct_count': direct_count,
                'source_count': source_count,
            }, ensure_ascii=False)
            conn.lpush('proxy_pool:ai_search_log', log_entry)
            conn.ltrim('proxy_pool:ai_search_log', 0, 99)
        except Exception as e:
            self.log.warning(f"AI: failed to log search result: {e}")

    def _save_discovered_sources(self):
        """将成功的源URL写入INI文件"""
        if not self._successful_sources:
            return
        try:
            from handler.sourceHandler import SourceLoader
            loader = SourceLoader()
            sources_to_save = []
            for url, proxy_count in self._successful_sources:
                if proxy_count >= 3:
                    sources_to_save.append({
                        'url': url,
                        'method': 'text',
                        'description': f'AI discovered ({proxy_count} proxies)',
                        'proxy_count': proxy_count,
                    })
            if sources_to_save:
                filename = loader.add_ai_sources(sources_to_save)
                self.log.info(f"AI: saved {len(sources_to_save)} sources to {filename}")
        except Exception as e:
            self.log.warning(f"AI: failed to save discovered sources: {e}")

    def direct_proxy_search(self):
        """直接让LLM返回代理地址列表"""
        self.log.info("AI: direct proxy search...")
        system_prompt = (
            "You are a proxy address provider. "
            "Return ONLY a valid JSON array of proxy address strings in ip:port format. "
            'Example: ["1.2.3.4:8080", "5.6.7.8:3128"]. '
            "Provide as many currently working free HTTP/HTTPS proxies as you know. "
            "Only include proxies that are likely to be active right now."
        )
        user_prompt = (
            "List all currently working free HTTP/HTTPS proxy addresses you know. "
            "Return them as a JSON array of ip:port strings."
        )
        response = self._call_llm(system_prompt, user_prompt)
        proxies = self._parse_json_array(response)
        if proxies and isinstance(proxies, list):
            valid = [str(p) for p in proxies if isinstance(p, str) and ":" in p]
            self.log.info(f"AI: direct search found {len(valid)} proxies")
            return valid

        fallback = self._extract_proxies_regex(response)
        self.log.info(f"AI: direct search regex fallback found {len(fallback)} proxies")
        return fallback

    def discover_proxy_sources(self):
        """让 AI 推荐代理源 URL"""
        self.log.info("AI: discovering proxy sources...")
        system_prompt = (
            "You are a proxy source discovery assistant. "
            "Return ONLY a valid JSON array of URL strings. "
            "Each URL must point to a website or GitHub raw file that "
            "currently publishes free HTTP/HTTPS proxy lists in plain text. "
            f"Return at most {self.max_sources} URLs."
        )
        user_prompt = (
            "Find websites and GitHub raw file URLs that currently publish "
            "free HTTP/HTTPS proxy lists (ip:port format). Focus on sources that are "
            "updated frequently. Return the URLs as a JSON array."
        )
        response = self._call_llm(system_prompt, user_prompt)
        urls = self._parse_json_array(response)
        if urls and isinstance(urls, list):
            valid_urls = [u for u in urls if isinstance(u, str) and u.startswith("http")]
            self.log.info(f"AI: discovered {len(valid_urls)} proxy source URLs")
            return valid_urls[:self.max_sources]

        url_pattern = re.compile(r"https?://[^\s,\"']+")
        fallback = list(set(url_pattern.findall(response)))[:self.max_sources]
        self.log.info(f"AI: fallback URL extraction found {len(fallback)} URLs")
        return fallback

    def extract_proxies_from_url(self, url):
        """抓取网页并用正则+LLM提取代理地址"""
        self.log.info(f"AI: extracting proxies from {url}")
        try:
            resp = requests.get(url, timeout=10, verify=False,
                                headers={"User-Agent": "Mozilla/5.0"})
            content = resp.text[:10000]
        except Exception as e:
            self.log.warning(f"AI: failed to fetch {url}: {e}")
            return []

        regex_proxies = self._extract_proxies_regex(content)
        if len(regex_proxies) >= 5:
            self.log.info(f"AI: regex extracted {len(regex_proxies)} proxies from {url[:50]}")
            return regex_proxies

        system_prompt = (
            "Extract all proxy addresses in ip:port format. "
            "Return ONLY a JSON array like [\"1.2.3.4:8080\"]. "
            "If none found, return []."
        )
        user_prompt = f"Extract proxies from:\n{content[:4000]}"
        response = self._call_llm(system_prompt, user_prompt)
        proxies = self._parse_json_array(response)
        if proxies and isinstance(proxies, list):
            return [str(p) for p in proxies if isinstance(p, str) and ":" in p]

        return regex_proxies

    def search_proxies(self):
        """主流程：直接搜索 + 源发现提取，有整体超时限制"""
        if not self.enabled:
            self.log.info("AI search disabled (no API key configured)")
            return []

        start_time = time.time()
        all_proxies = set()
        self._successful_sources = []
        direct_count = 0
        source_count = 0

        try:
            direct = self.direct_proxy_search()
            all_proxies.update(direct)
            direct_count = len(direct)
            elapsed = time.time() - start_time
            self.log.info(f"AI: direct search done in {elapsed:.1f}s, {direct_count} proxies")

            if elapsed < self.SEARCH_HARD_LIMIT * 0.6:
                try:
                    sources = self.discover_proxy_sources()
                    source_count = len(sources)
                    for url in sources:
                        if time.time() - start_time > self.SEARCH_HARD_LIMIT:
                            self.log.warning("AI: search hard limit reached, stopping")
                            break
                        try:
                            proxies = self.extract_proxies_from_url(url)
                            all_proxies.update(proxies)
                            self.log.info(f"AI: {url[:50]}... -> {len(proxies)} proxies")
                            if len(proxies) >= 3:
                                self._successful_sources.append((url, len(proxies)))
                        except Exception as e:
                            self.log.warning(f"AI: error processing {url}: {e}")
                except Exception as e:
                    self.log.warning(f"AI: source discovery failed: {e}")
        except Exception as e:
            self.log.error(f"AI: search_proxies failed: {e}")

        elapsed = time.time() - start_time
        total = len(all_proxies)
        self.log.info(f"AI: search complete in {elapsed:.1f}s - {total} unique proxies")

        # 保存成功的源到INI文件
        self._save_discovered_sources()

        # 记录搜索结果日志到Redis
        self._log_search_result(total, direct_count, source_count)

        return list(all_proxies)
