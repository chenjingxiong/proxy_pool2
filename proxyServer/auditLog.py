# -*- coding: utf-8 -*-
"""
-------------------------------------------------
   File Name：     auditLog
   Description :   虚拟代理服务器审计日志 — 记录每次外部调用的详细信息
   date：          2026/06/16
-------------------------------------------------
"""

import os
import json
import time
import logging
from logging.handlers import RotatingFileHandler


class AuditLogger:
    """基于 RotatingFileHandler 的审计日志，JSON Lines 格式，按文件大小轮转"""

    def __init__(self, file_path="logs/virtual_proxy_audit.log", max_size_kb=1024, backup_count=5):
        self.max_size_kb = max_size_kb
        self.backup_count = backup_count
        os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)

        self._logger = logging.getLogger("virtual_proxy_audit")
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False

        handler = RotatingFileHandler(
            file_path,
            maxBytes=max_size_kb * 1024,
            backupCount=backup_count,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
        self._logger.addHandler(handler)

    def log(self, client, method, target, proxy, success, status, duration, error=""):
        entry = {
            "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
            "client": client,
            "method": method,
            "target": target,
            "proxy": proxy,
            "success": success,
            "status": status,
            "duration": duration,
        }
        if error:
            entry["error"] = error
        self._logger.info(json.dumps(entry, ensure_ascii=False))
