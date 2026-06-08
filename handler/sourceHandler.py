# -*- coding: utf-8 -*-
"""
   sourceHandler - 代理源配置加载器
   从 conf/sources/*.ini 加载代理源配置，支持内置源和AI发现的源
"""
import os
import glob
import time
import json
import configparser
from collections import namedtuple

import setting
from util.six import withMetaclass
from util.singleton import Singleton

SourceConfig = namedtuple('SourceConfig', [
    'name', 'type', 'description', 'category', 'enabled',
    'url', 'method', 'json_path', 'source_file',
])

SOURCES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           'conf', 'sources')


class SourceLoader(withMetaclass(Singleton)):

    def __init__(self, sources_dir=None):
        self._sources_dir = sources_dir or SOURCES_DIR
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
            self._file_mtimes[ini_path] = os.path.getmtime(ini_path)
            self._parse_ini(ini_path)

    def _parse_ini(self, ini_path):
        """解析单个INI文件"""
        filename = os.path.basename(ini_path)
        is_ai = filename.startswith('AI-')

        config = configparser.ConfigParser()
        config.read(ini_path, encoding='utf-8')

        for section in config.sections():
            src_type = config.get(section, 'type', fallback='builtin')
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
        return [s for s in self.get_all_sources() if s.type != 'builtin']

    def add_ai_sources(self, discovered_urls):
        """
        AI发现的代理源写入新的INI文件
        discovered_urls: list of dict {url, method, description, proxy_count}
        """
        if not discovered_urls:
            return

        os.makedirs(self._sources_dir, exist_ok=True)

        now = time.strftime('%Y-%m-%d-%H%M')
        filename = f'AI-{now}.ini'
        filepath = os.path.join(self._sources_dir, filename)

        config = configparser.ConfigParser()
        config.set('DEFAULT', 'created', time.strftime('%Y-%m-%d %H:%M:%S'))
        config.set('DEFAULT', 'total_sources', str(len(discovered_urls)))

        for i, item in enumerate(discovered_urls, 1):
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
