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


def testAiSearchExtractProxiesFromUrl():
    """测试从URL提取代理（mock HTTP请求和LLM调用）"""
    with patch.object(ConfigHandler, 'aiApiKey', 'test-key', create=True):
        with patch.object(ConfigHandler, 'aiApiBaseUrl', 'https://api.openai.com/v1', create=True):
            with patch.object(ConfigHandler, 'aiModel', 'gpt-3.5-turbo', create=True):
                with patch.object(ConfigHandler, 'aiApiTimeout', 60, create=True):
                    with patch.object(ConfigHandler, 'aiMaxSources', 10, create=True):
                        ai = AISearch()

                        # mock requests.get 返回含代理的网页
                        mock_resp = MagicMock()
                        mock_resp.text = "1.2.3.4:8080\n5.6.7.8:3128\n9.10.11.12:1080"
                        mock_resp.raise_for_status = MagicMock()

                        # mock LLM 返回 JSON 数组
                        mock_llm_resp = MagicMock()
                        mock_llm_resp.raise_for_status = MagicMock()
                        mock_llm_resp.json.return_value = {
                            "choices": [{"message": {"content": '["1.2.3.4:8080","5.6.7.8:3128"]'}}]
                        }

                        with patch('requests.get', return_value=mock_resp):
                            with patch('requests.post', return_value=mock_llm_resp):
                                proxies = ai.extract_proxies_from_url("http://example.com/proxies")
                                assert isinstance(proxies, list)
                                assert len(proxies) >= 1


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


def testAiSearchDiscoverSources():
    """测试AI发现代理源（mock LLM调用）"""
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


def testConfigHandlerAiDefaults():
    """测试AI配置项默认值"""
    conf = ConfigHandler()
    # 在无环境变量时应返回 setting.py 中的默认值
    assert isinstance(conf.aiApiBaseUrl, str)
    assert isinstance(conf.aiModel, str)
    assert isinstance(conf.aiSearchHour, int)
    assert isinstance(conf.aiMaxSources, int)
    assert isinstance(conf.aiApiTimeout, int)


if __name__ == '__main__':
    testAiSearchDisabled()
    print("PASS: testAiSearchDisabled")
    testAiSearchExtractProxiesFromUrl()
    print("PASS: testAiSearchExtractProxiesFromUrl")
    testAiSearchParseJsonArray()
    print("PASS: testAiSearchParseJsonArray")
    testAiSearchDiscoverSources()
    print("PASS: testAiSearchDiscoverSources")
    testConfigHandlerAiDefaults()
    print("PASS: testConfigHandlerAiDefaults")
    print("\nAll AI search tests passed!")
