# -*- coding: utf-8 -*-
"""
-------------------------------------------------
   File Name：     configHandler
   Description :
   Author :        JHao
   date：          2020/6/22
-------------------------------------------------
   Change Activity:
                   2020/6/22:
                   2026/06/16: 新增系统配置（保鲜间隔/选取权重）
-------------------------------------------------
"""
__author__ = 'JHao'

import os
import configparser
import setting
from util.singleton import Singleton
from util.lazyProperty import LazyProperty
from util.six import reload_six, withMetaclass

AI_CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'conf', 'ai_config.ini'
)

SYSTEM_CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'conf', 'system_config.ini'
)

_AI_PROPERTIES = [
    'aiApiKey', 'aiApiBaseUrl', 'aiModel',
    'aiSearchEnabled', 'aiSearchHour', 'aiMaxSources', 'aiApiTimeout',
]

_SYSTEM_PROPERTIES = [
    'refreshIntervalMin', 'weightRecency', 'weightSpeed',
]


def _load_system_config():
    """读取 conf/system_config.ini, 环境变量优先覆盖（仅内存，不写回磁盘）"""
    result = {}
    config = configparser.ConfigParser()
    if os.path.isfile(SYSTEM_CONFIG_FILE):
        config.read(SYSTEM_CONFIG_FILE, encoding='utf-8')
        if config.has_section('system'):
            result = dict(config.items('system'))

    # 环境变量覆盖（仅内存）
    env_override = {
        'refresh_interval_min': os.getenv('PROXY_REFRESH_INTERVAL_MIN', ''),
        'weight_recency': os.getenv('PROXY_WEIGHT_RECENCY', ''),
        'weight_speed': os.getenv('PROXY_WEIGHT_SPEED', ''),
    }
    for k, v in env_override.items():
        if v:
            result[k] = v

    return result


def _get_system_env_sourced_keys():
    env_map = {
        'refresh_interval_min': os.getenv('PROXY_REFRESH_INTERVAL_MIN', ''),
        'weight_recency': os.getenv('PROXY_WEIGHT_RECENCY', ''),
        'weight_speed': os.getenv('PROXY_WEIGHT_SPEED', ''),
    }
    return [k for k, v in env_map.items() if v]


def _load_ai_config():
    """读取 conf/ai_config.ini, 环境变量优先覆盖（仅内存，不写回磁盘）"""
    result = {}
    config = configparser.ConfigParser()
    if os.path.isfile(AI_CONFIG_FILE):
        config.read(AI_CONFIG_FILE, encoding='utf-8')
        if config.has_section('ai'):
            result = dict(config.items('ai'))
    else:
        # 首次启动：INI 不存在时从环境变量 seed 一份
        env_seed = {
            'api_key': os.getenv('AI_API_KEY', ''),
            'api_base_url': os.getenv('AI_API_BASE_URL', ''),
            'model': os.getenv('AI_MODEL', ''),
            'search_hour': os.getenv('AI_SEARCH_HOUR', ''),
            'max_sources': os.getenv('AI_MAX_SOURCES', ''),
            'api_timeout': os.getenv('AI_API_TIMEOUT', ''),
        }
        env_se_enabled = os.getenv('AI_SEARCH_ENABLED')
        if env_se_enabled is not None:
            env_seed['search_enabled'] = 'true' if env_se_enabled.lower() in ('1', 'true', 'yes') else 'false'
        elif os.getenv('AI_API_KEY'):
            env_seed['search_enabled'] = 'true'
        else:
            env_seed['search_enabled'] = 'false'

        has_any = any(v for v in env_seed.values())
        if has_any:
            env_sourced_keys = [k for k, v in env_seed.items() if v]
            config.add_section('ai')
            for k, v in env_seed.items():
                if v:
                    config.set('ai', k, v)
            config.add_section('metadata')
            config.set('metadata', 'env_sourced', ','.join(env_sourced_keys))
            os.makedirs(os.path.dirname(AI_CONFIG_FILE), exist_ok=True)
            with open(AI_CONFIG_FILE, 'w', encoding='utf-8') as f:
                config.write(f)
            result = {k: v for k, v in env_seed.items() if v}

    # 环境变量覆盖（仅内存）— 修复 .env 修改后不生效的问题
    env_override = {
        'api_key': os.getenv('AI_API_KEY', ''),
        'api_base_url': os.getenv('AI_API_BASE_URL', ''),
        'model': os.getenv('AI_MODEL', ''),
        'search_hour': os.getenv('AI_SEARCH_HOUR', ''),
        'max_sources': os.getenv('AI_MAX_SOURCES', ''),
        'api_timeout': os.getenv('AI_API_TIMEOUT', ''),
    }
    env_se_enabled = os.getenv('AI_SEARCH_ENABLED')
    if env_se_enabled is not None:
        env_override['search_enabled'] = 'true' if env_se_enabled.lower() in ('1', 'true', 'yes') else 'false'
    for k, v in env_override.items():
        if v:
            result[k] = v

    return result


def _get_env_sourced_keys():
    """返回当前由环境变量提供的配置项（实际非空的环境变量）"""
    env_map = {
        'api_key': os.getenv('AI_API_KEY', ''),
        'api_base_url': os.getenv('AI_API_BASE_URL', ''),
        'model': os.getenv('AI_MODEL', ''),
        'search_hour': os.getenv('AI_SEARCH_HOUR', ''),
        'max_sources': os.getenv('AI_MAX_SOURCES', ''),
        'api_timeout': os.getenv('AI_API_TIMEOUT', ''),
    }
    se = os.getenv('AI_SEARCH_ENABLED')
    if se is not None:
        env_map['search_enabled'] = se
    return [k for k, v in env_map.items() if v]


class ConfigHandler(withMetaclass(Singleton)):

    def __init__(self):
        pass

    @classmethod
    def save_ai_config(cls, data):
        """写入 AI 配置到 INI 文件并清除缓存"""
        # 如果环境变量有值且 UI 传来空值，保留环境变量的值
        env_protection = {
            'api_key': os.getenv('AI_API_KEY', ''),
            'api_base_url': os.getenv('AI_API_BASE_URL', ''),
            'model': os.getenv('AI_MODEL', ''),
            'search_hour': os.getenv('AI_SEARCH_HOUR', ''),
            'max_sources': os.getenv('AI_MAX_SOURCES', ''),
            'api_timeout': os.getenv('AI_API_TIMEOUT', ''),
        }
        for k, env_val in env_protection.items():
            if env_val and not data.get(k, ''):
                data[k] = env_val

        config = configparser.ConfigParser()
        config.add_section('ai')
        mapping = {
            'api_key': data.get('api_key', ''),
            'api_base_url': data.get('api_base_url', ''),
            'model': data.get('model', ''),
            'search_enabled': 'true' if data.get('search_enabled') else 'false',
            'search_hour': str(data.get('search_hour', 3)),
            'max_sources': str(data.get('max_sources', 10)),
            'api_timeout': str(data.get('api_timeout', 60)),
        }
        for k, v in mapping.items():
            config.set('ai', k, v)
        # 保留 metadata section
        env_sourced = _get_env_sourced_keys()
        if env_sourced:
            config.add_section('metadata')
            config.set('metadata', 'env_sourced', ','.join(env_sourced))

        os.makedirs(os.path.dirname(AI_CONFIG_FILE), exist_ok=True)
        with open(AI_CONFIG_FILE, 'w', encoding='utf-8') as f:
            config.write(f)

        # 清除 Singleton 实例上的 LazyProperty 缓存
        inst = cls()
        for prop in _AI_PROPERTIES:
            if hasattr(inst, prop):
                delattr(inst, prop)

    @classmethod
    def save_system_config(cls, data):
        """写入系统配置到 INI 文件并清除缓存"""
        # 环境变量保护：若环境变量有值且 UI 传来空值，保留环境变量
        env_protection = {
            'refresh_interval_min': os.getenv('PROXY_REFRESH_INTERVAL_MIN', ''),
            'weight_recency': os.getenv('PROXY_WEIGHT_RECENCY', ''),
            'weight_speed': os.getenv('PROXY_WEIGHT_SPEED', ''),
        }
        for k, env_val in env_protection.items():
            if env_val and not data.get(k, ''):
                data[k] = env_val

        config = configparser.ConfigParser()
        config.add_section('system')
        mapping = {
            'refresh_interval_min': str(data.get('refresh_interval_min', setting.PROXY_REFRESH_INTERVAL_MIN)),
            'weight_recency': str(data.get('weight_recency', setting.PROXY_WEIGHT_RECENCY)),
            'weight_speed': str(data.get('weight_speed', setting.PROXY_WEIGHT_SPEED)),
        }
        for k, v in mapping.items():
            config.set('system', k, v)

        env_sourced = _get_system_env_sourced_keys()
        if env_sourced:
            config.add_section('metadata')
            config.set('metadata', 'env_sourced', ','.join(env_sourced))

        os.makedirs(os.path.dirname(SYSTEM_CONFIG_FILE), exist_ok=True)
        with open(SYSTEM_CONFIG_FILE, 'w', encoding='utf-8') as f:
            config.write(f)

        inst = cls()
        for prop in _SYSTEM_PROPERTIES:
            if hasattr(inst, prop):
                delattr(inst, prop)

    @LazyProperty
    def serverHost(self):
        return os.environ.get("HOST", setting.HOST)

    @LazyProperty
    def serverPort(self):
        return os.environ.get("PORT", setting.PORT)

    @LazyProperty
    def dbConn(self):
        return os.getenv("DB_CONN", setting.DB_CONN)

    @LazyProperty
    def tableName(self):
        return os.getenv("TABLE_NAME", setting.TABLE_NAME)

    @property
    def fetchers(self):
        from handler.sourceHandler import SourceLoader
        loader = SourceLoader()
        names = loader.get_fetcher_names()
        if names:
            return names
        reload_six(setting)
        return setting.PROXY_FETCHER

    @LazyProperty
    def httpUrl(self):
        return os.getenv("HTTP_URL", setting.HTTP_URL)

    @LazyProperty
    def httpsUrl(self):
        return os.getenv("HTTPS_URL", setting.HTTPS_URL)

    @LazyProperty
    def verifyTimeout(self):
        return int(os.getenv("VERIFY_TIMEOUT", setting.VERIFY_TIMEOUT))

    # @LazyProperty
    # def proxyCheckCount(self):
    #     return int(os.getenv("PROXY_CHECK_COUNT", setting.PROXY_CHECK_COUNT))

    @LazyProperty
    def maxFailCount(self):
        return int(os.getenv("MAX_FAIL_COUNT", setting.MAX_FAIL_COUNT))

    # @LazyProperty
    # def maxFailRate(self):
    #     return int(os.getenv("MAX_FAIL_RATE", setting.MAX_FAIL_RATE))

    @LazyProperty
    def poolSizeMin(self):
        return int(os.getenv("POOL_SIZE_MIN", setting.POOL_SIZE_MIN))

    @LazyProperty
    def proxyRegion(self):
        return bool(os.getenv("PROXY_REGION", setting.PROXY_REGION))

    @LazyProperty
    def proxyDomain(self):
        return os.getenv("PROXY_DOMAIN", "").rstrip("/").strip()

    @LazyProperty
    def apiBaseUrl(self):
        if self.proxyDomain:
            return self.proxyDomain
        return "http://{host}:{port}".format(host=self.serverHost, port=self.serverPort)

    @LazyProperty
    def virtualProxyUrl(self):
        if self.proxyDomain:
            return self.proxyDomain.replace("https://", "http://").replace("http://", "")
        return "{host}:{port}".format(host=self.serverHost, port=5010)

    @LazyProperty
    def timezone(self):
        return os.getenv("TIMEZONE", setting.TIMEZONE)

    def _ai_cfg(self, key, default):
        ini = _load_ai_config()
        val = ini.get(key, '')
        return val if val else default

    @LazyProperty
    def aiApiKey(self):
        return self._ai_cfg('api_key', os.getenv("AI_API_KEY", setting.AI_API_KEY))

    @LazyProperty
    def aiApiBaseUrl(self):
        return self._ai_cfg('api_base_url', os.getenv("AI_API_BASE_URL", setting.AI_API_BASE_URL))

    @LazyProperty
    def aiModel(self):
        return self._ai_cfg('model', os.getenv("AI_MODEL", setting.AI_MODEL))

    @LazyProperty
    def aiSearchEnabled(self):
        ini = _load_ai_config()
        if 'search_enabled' in ini:
            return ini['search_enabled'].lower() in ('1', 'true', 'yes')
        env_val = os.getenv("AI_SEARCH_ENABLED")
        if env_val is not None:
            return env_val.lower() in ("1", "true", "yes")
        return bool(self.aiApiKey)

    @LazyProperty
    def aiSearchHour(self):
        return int(self._ai_cfg('search_hour', os.getenv("AI_SEARCH_HOUR", setting.AI_SEARCH_HOUR)))

    @LazyProperty
    def aiMaxSources(self):
        return int(self._ai_cfg('max_sources', os.getenv("AI_MAX_SOURCES", setting.AI_MAX_SOURCES)))

    @LazyProperty
    def aiApiTimeout(self):
        return int(self._ai_cfg('api_timeout', os.getenv("AI_API_TIMEOUT", setting.AI_API_TIMEOUT)))

    def _system_cfg(self, key, default):
        ini = _load_system_config()
        val = ini.get(key, '')
        return val if val else default

    @LazyProperty
    def refreshIntervalMin(self):
        return int(self._system_cfg('refresh_interval_min',
                                     os.getenv("PROXY_REFRESH_INTERVAL_MIN", setting.PROXY_REFRESH_INTERVAL_MIN)))

    @LazyProperty
    def weightRecency(self):
        return float(self._system_cfg('weight_recency',
                                       os.getenv("PROXY_WEIGHT_RECENCY", setting.PROXY_WEIGHT_RECENCY)))

    @LazyProperty
    def weightSpeed(self):
        return float(self._system_cfg('weight_speed',
                                       os.getenv("PROXY_WEIGHT_SPEED", setting.PROXY_WEIGHT_SPEED)))

