# -*- coding: utf-8 -*-
"""
   sourceHandler - 代理源配置加载器
   从 conf/sources/*.ini 加载代理源配置，支持内置源、AI 发现源、自定义订阅
"""
import os
import glob
import time
import configparser
from collections import namedtuple

import setting
from util.six import withMetaclass
from util.singleton import Singleton

SourceConfig = namedtuple('SourceConfig', [
    'name', 'type', 'description', 'category', 'enabled',
    'url', 'method', 'json_path', 'source_file', 'content',
])

SOURCES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           'conf', 'sources')

SUBSCRIPTIONS_FILE = os.path.join(SOURCES_DIR, 'subscriptions.ini')

# 支持的订阅 / 节点类型
SUBSCRIPTION_TYPES = {
    'subscription',     # HTTP/TXT 订阅 URL（base64/明文混排）
    'clash_yaml',       # Clash YAML 订阅 URL
    'single_node',      # 单节点 URI 直接粘贴
    'plain_uri_list',   # 多行 URI 直接粘贴
}


class SourceLoader(withMetaclass(Singleton)):

    def __init__(self, sources_dir=None):
        self._sources_dir = sources_dir or SOURCES_DIR
        self._subscriptions_file = SUBSCRIPTIONS_FILE
        if sources_dir:
            self._subscriptions_file = os.path.join(sources_dir, 'subscriptions.ini')
        self._sources = {}
        self._file_mtimes = {}
        self._load_all()

    def _load_all(self):
        """扫描并加载所有INI源配置文件"""
        self._sources = {}
        self._file_mtimes = {}

        if not os.path.isdir(self._sources_dir):
            return

        ini_files = sorted(glob.glob(os.path.join(self._sources_dir, '*.ini')))
        for ini_path in ini_files:
            try:
                self._file_mtimes[ini_path] = os.path.getmtime(ini_path)
            except OSError:
                continue
            self._parse_ini(ini_path)

    def _parse_ini(self, ini_path):
        """解析单个INI文件"""
        filename = os.path.basename(ini_path)
        is_ai = filename.startswith('AI-')

        config = configparser.ConfigParser()
        config.read(ini_path, encoding='utf-8')

        for section in config.sections():
            src_type = config.get(section, 'type', fallback='builtin')
            # 读取 content 字段（仅订阅 / 节点类有）
            content = ""
            if config.has_option(section, 'content'):
                content = config.get(section, 'content', fallback='')
            src = SourceConfig(
                name=section,
                type=src_type,
                description=config.get(section, 'description', fallback=section),
                category=config.get(section, 'category', fallback='http'),
                enabled=config.getboolean(section, 'enabled', fallback=True),
                url=config.get(section, 'url', fallback=''),
                method=config.get(section, 'method', fallback=''),
                json_path=config.get(section, 'json_path', fallback=''),
                source_file=filename,
                content=content,
            )
            # 同名源后加载的覆盖先加载的
            self._sources[section] = src

    def reload(self):
        """检查文件变更并重新加载"""
        need_reload = False

        if not os.path.isdir(self._sources_dir):
            return

        ini_files = glob.glob(os.path.join(self._sources_dir, '*.ini'))

        # 新文件出现或文件修改时间变化
        current_mtimes = {}
        for ini_path in ini_files:
            try:
                current_mtimes[ini_path] = os.path.getmtime(ini_path)
            except OSError:
                continue

        if set(current_mtimes.keys()) != set(self._file_mtimes.keys()):
            need_reload = True
        else:
            for path, mtime in current_mtimes.items():
                if self._file_mtimes.get(path) != mtime:
                    need_reload = True
                    break

        if need_reload:
            self._load_all()

    def get_fetcher_names(self):
        """返回所有启用的源名称列表（供Fetcher使用）"""
        self.reload()
        if self._sources:
            return [name for name, src in self._sources.items() if src.enabled]
        # fallback: 没有INI文件时返回setting中的列表
        from util.six import reload_six
        reload_six(setting)
        return setting.PROXY_FETCHER

    def get_source(self, name):
        """获取单个源配置"""
        self.reload()
        return self._sources.get(name)

    def get_all_sources(self):
        """返回所有源的完整元数据列表"""
        self.reload()
        return list(self._sources.values())

    def get_builtin_sources(self):
        """返回内置源列表"""
        return [s for s in self.get_all_sources() if s.type == 'builtin']

    def get_ai_sources(self):
        """返回AI发现的源列表"""
        return [s for s in self.get_all_sources()
                if s.type not in ('builtin',) and s.type not in SUBSCRIPTION_TYPES]

    def get_subscription_sources(self):
        """返回用户自定义订阅/节点列表"""
        return [s for s in self.get_all_sources() if s.type in SUBSCRIPTION_TYPES]

    def add_ai_source(self, discovered_urls):
        """
        AI发现的代理源写入新的INI文件（带URL去重）
        discovered_urls: list of dict {url, method, description, proxy_count}
        """
        if not discovered_urls:
            return

        # 去重：收集已存在的 URL
        existing_urls = set()
        for src in self.get_all_sources():
            if src.type not in ('builtin',) and src.type not in SUBSCRIPTION_TYPES and src.url:
                existing_urls.add(src.url)

        new_sources = [item for item in discovered_urls
                       if item.get('url', '') not in existing_urls]

        if not new_sources:
            return

        os.makedirs(self._sources_dir, exist_ok=True)

        now = time.strftime('%Y-%m-%d-%H%M')
        filename = f'AI-{now}.ini'
        filepath = os.path.join(self._sources_dir, filename)

        config = configparser.ConfigParser()
        config.set('DEFAULT', 'created', time.strftime('%Y-%m-%d %H:%M:%S'))
        config.set('DEFAULT', 'total_sources', str(len(new_sources)))

        for i, item in enumerate(new_sources, 1):
            section = f'source_{i}'
            config.add_section(section)
            config.set(section, 'type', 'url_text')
            config.set(section, 'url', item.get('url', ''))
            config.set(section, 'method', item.get('method', 'text'))
            config.set(section, 'description', item.get('description', ''))
            config.set(section, 'category', 'http')
            config.set(section, 'enabled', 'true')
            if item.get('proxy_count'):
                config.set(section, 'proxy_count', str(item['proxy_count']))

        with open(filepath, 'w', encoding='utf-8') as f:
            config.write(f)

        self._load_all()
        return filename

    # ==================== 订阅 / 节点 CRUD ====================

    def add_subscription(self, name, src_type, url="", content="", description="", enabled=True):
        """新增订阅/节点；name 已存在则抛 ValueError"""
        if src_type not in SUBSCRIPTION_TYPES:
            raise ValueError(f"unsupported subscription type: {src_type}")
        if not name:
            raise ValueError("name is required")
        # 名称只能字母/数字/下划线/连字符（INI section 限制）
        if not _valid_section_name(name):
            raise ValueError("name must be alphanumeric, dot, underscore, or hyphen")

        self.reload()
        if name in self._sources:
            raise ValueError(f"subscription '{name}' already exists")

        if src_type in ('subscription', 'clash_yaml') and not url:
            raise ValueError(f"type '{src_type}' requires url")
        if src_type in ('single_node', 'plain_uri_list') and not content:
            raise ValueError(f"type '{src_type}' requires content")

        os.makedirs(self._sources_dir, exist_ok=True)

        config = configparser.ConfigParser()
        if os.path.isfile(self._subscriptions_file):
            config.read(self._subscriptions_file, encoding='utf-8')

        if not config.has_section(name):
            config.add_section(name)
        config.set(name, 'type', src_type)
        config.set(name, 'description', description or name)
        config.set(name, 'category', 'subscription')
        config.set(name, 'enabled', 'true' if enabled else 'false')
        if url:
            config.set(name, 'url', url)
        if content:
            # 多行 content 保留换行（configparser 自动处理）
            config.set(name, 'content', content)

        with open(self._subscriptions_file, 'w', encoding='utf-8') as f:
            config.write(f)

        self._load_all()
        return self._sources.get(name)

    def update_subscription(self, name, **kwargs):
        """修改订阅；不存在则抛 ValueError"""
        self.reload()
        if name not in self._sources:
            raise ValueError(f"subscription '{name}' not found")

        config = configparser.ConfigParser()
        config.read(self._subscriptions_file, encoding='utf-8')
        if not config.has_section(name):
            raise ValueError(f"subscription '{name}' not in subscriptions.ini")

        for key in ('type', 'url', 'content', 'description', 'category'):
            if key in kwargs and kwargs[key] is not None:
                config.set(name, key, str(kwargs[key]))
        if 'enabled' in kwargs and kwargs['enabled'] is not None:
            config.set(name, 'enabled', 'true' if kwargs['enabled'] else 'false')

        with open(self._subscriptions_file, 'w', encoding='utf-8') as f:
            config.write(f)

        self._load_all()
        return self._sources.get(name)

    def remove_subscription(self, name):
        """删除订阅；不存在返回 False"""
        self.reload()
        if name not in self._sources:
            return False
        src = self._sources[name]
        if src.source_file != 'subscriptions.ini':
            # 不允许通过此接口删除非订阅文件中的源
            return False

        config = configparser.ConfigParser()
        config.read(self._subscriptions_file, encoding='utf-8')
        if config.has_section(name):
            config.remove_section(name)
            with open(self._subscriptions_file, 'w', encoding='utf-8') as f:
                config.write(f)
            self._load_all()
            return True
        return False

    def get_subscription(self, name):
        """读取单个订阅配置；不存在返回 None"""
        self.reload()
        return self._sources.get(name)


def _valid_section_name(name):
    """INI section 名称合法性校验"""
    if not name:
        return False
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
    return all(c in allowed for c in name)
