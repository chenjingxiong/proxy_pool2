# -*- coding: utf-8 -*-
"""
   testAISearch - AI代理搜索功能测试
"""
import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from helper.aiSearch import AISearch
from handler.configHandler import ConfigHandler


def testAiSearchDisabled():
    """无API Key时AI搜索应禁用"""
    with patch.object(ConfigHandler, 'aiApiKey', '', create=True):
        with patch.object(ConfigHandler, 'aiApiBaseUrl', 'https://api.openai.com/v1', create=True):
            with patch.object(ConfigHandler, 'aiModel', 'gpt-3.5-turbo', create=True):
                with patch.object(ConfigHandler, 'aiApiTimeout', 60, create=True):
                    with patch.object(ConfigHandler, 'aiMaxSources', 10, create=True):
                        ai = AISearch()
                        assert ai.enabled is False
                        result = ai.search_proxies()
                        assert result == []


def testAiSearchParseJsonArray():
    """测试JSON数组解析"""
    with patch.object(ConfigHandler, 'aiApiKey', 'test-key', create=True):
        with patch.object(ConfigHandler, 'aiApiBaseUrl', 'https://api.openai.com/v1', create=True):
            with patch.object(ConfigHandler, 'aiModel', 'gpt-3.5-turbo', create=True):
                with patch.object(ConfigHandler, 'aiApiTimeout', 60, create=True):
                    with patch.object(ConfigHandler, 'aiMaxSources', 10, create=True):
                        ai = AISearch()
                        assert ai._parse_json_array('["a","b"]') == ["a", "b"]
                        assert ai._parse_json_array('Some text ["a","b"] more') == ["a", "b"]
                        assert ai._parse_json_array('no json here') == []


def testExtractProxiesRegex():
    """测试正则提取代理"""
    with patch.object(ConfigHandler, 'aiApiKey', 'test-key', create=True):
        with patch.object(ConfigHandler, 'aiApiBaseUrl', 'https://api.openai.com/v1', create=True):
            with patch.object(ConfigHandler, 'aiModel', 'gpt-3.5-turbo', create=True):
                with patch.object(ConfigHandler, 'aiApiTimeout', 60, create=True):
                    with patch.object(ConfigHandler, 'aiMaxSources', 10, create=True):
                        ai = AISearch()
                        text = "1.2.3.4:8080\n5.6.7.8:3128\n192.168.1.1:1080"
                        proxies = ai._extract_proxies_regex(text)
                        assert len(proxies) == 3
                        assert "1.2.3.4:8080" in proxies


def testDirectProxySearch():
    """测试直接代理搜索"""
    with patch.object(ConfigHandler, 'aiApiKey', 'test-key', create=True):
        with patch.object(ConfigHandler, 'aiApiBaseUrl', 'https://api.openai.com/v1', create=True):
            with patch.object(ConfigHandler, 'aiModel', 'gpt-3.5-turbo', create=True):
                with patch.object(ConfigHandler, 'aiApiTimeout', 60, create=True):
                    with patch.object(ConfigHandler, 'aiMaxSources', 10, create=True):
                        ai = AISearch()

                        mock_resp = MagicMock()
                        mock_resp.raise_for_status = MagicMock()
                        mock_resp.json.return_value = {
                            "choices": [{"message": {"content": '["1.2.3.4:8080","5.6.7.8:3128"]'}}]
                        }

                        with patch('requests.post', return_value=mock_resp):
                            proxies = ai.direct_proxy_search()
                            assert isinstance(proxies, list)
                            assert len(proxies) >= 1


def testDiscoverSources():
    """测试AI发现代理源"""
    with patch.object(ConfigHandler, 'aiApiKey', 'test-key', create=True):
        with patch.object(ConfigHandler, 'aiApiBaseUrl', 'https://api.openai.com/v1', create=True):
            with patch.object(ConfigHandler, 'aiModel', 'gpt-3.5-turbo', create=True):
                with patch.object(ConfigHandler, 'aiApiTimeout', 60, create=True):
                    with patch.object(ConfigHandler, 'aiMaxSources', 3, create=True):
                        ai = AISearch()

                        mock_resp = MagicMock()
                        mock_resp.raise_for_status = MagicMock()
                        mock_resp.json.return_value = {
                            "choices": [{"message": {"content": '["https://example1.com","https://example2.com"]'}}]
                        }

                        with patch('requests.post', return_value=mock_resp):
                            urls = ai.discover_proxy_sources()
                            assert isinstance(urls, list)
                            assert len(urls) == 2
                            assert urls[0] == "https://example1.com"


def testExtractFromUrlRegex():
    """测试从URL提取代理（正则路径，无LLM调用）"""
    with patch.object(ConfigHandler, 'aiApiKey', 'test-key', create=True):
        with patch.object(ConfigHandler, 'aiApiBaseUrl', 'https://api.openai.com/v1', create=True):
            with patch.object(ConfigHandler, 'aiModel', 'gpt-3.5-turbo', create=True):
                with patch.object(ConfigHandler, 'aiApiTimeout', 60, create=True):
                    with patch.object(ConfigHandler, 'aiMaxSources', 10, create=True):
                        ai = AISearch()

                        mock_resp = MagicMock()
                        mock_resp.text = "1.2.3.4:8080\n5.6.7.8:3128\n9.10.11.12:1080\n13.14.15.16:80\n17.18.19.20:443\n21.22.23.24:9999"

                        with patch('requests.get', return_value=mock_resp):
                            proxies = ai.extract_proxies_from_url("http://example.com/proxies")
                            assert isinstance(proxies, list)
                            assert len(proxies) >= 5  # regex should find all 6


def testConfigDefaults():
    """测试AI配置项默认值"""
    conf = ConfigHandler()
    assert isinstance(conf.aiApiBaseUrl, str)
    assert isinstance(conf.aiModel, str)
    assert isinstance(conf.aiSearchHour, int)
    assert isinstance(conf.aiMaxSources, int)
    assert isinstance(conf.aiApiTimeout, int)


if __name__ == '__main__':
    tests = [
        ("testAiSearchDisabled", testAiSearchDisabled),
        ("testAiSearchParseJsonArray", testAiSearchParseJsonArray),
        ("testExtractProxiesRegex", testExtractProxiesRegex),
        ("testDirectProxySearch", testDirectProxySearch),
        ("testDiscoverSources", testDiscoverSources),
        ("testExtractFromUrlRegex", testExtractFromUrlRegex),
        ("testConfigDefaults", testConfigDefaults),
    ]
    passed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS: {name}")
            passed += 1
        except Exception as e:
            print(f"FAIL: {name} - {e}")
    print(f"\n{passed}/{len(tests)} tests passed")
