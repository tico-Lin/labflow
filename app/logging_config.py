"""
結構化日誌配置模組

【功能】
配置 Python 日誌系統，支援結構化日誌輸出（JSON 格式）、
日誌級別、日誌輪轉（根據時間和大小）等功能

【使用方式】
from app.logging_config import configure_logging, get_logger

configure_logging(level="INFO")
logger = get_logger(__name__)
logger.info("Application started")

【日誌級別】
- DEBUG: 詳細調試信息
- INFO: 重要事件和狀態更新
- WARNING: 警告訊息（不是錯誤）
- ERROR: 錯誤
- CRITICAL: 嚴重錯誤
"""

import logging
import logging.handlers
import json
import os
import sys
from datetime import datetime
from typing import Optional
from pathlib import Path

# 日誌配置
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.getenv("LOG_FORMAT", "text")  # text 或 json
LOG_FILE = os.getenv("LOG_FILE", "logs/labflow.log")
LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", str(10 * 1024 * 1024)))  # 10 MB
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))


# ============================================================================
# 自定義日誌格式化器
# ============================================================================

class StructuredFormatter(logging.Formatter):
    """結構化日誌格式化器（JSON 格式）"""
    
    def format(self, record: logging.LogRecord) -> str:
        """將日誌記錄格式化為 JSON"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # 添加額外信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # 添加自定義字段（如果有）
        if hasattr(record, "custom_fields"):
            log_data.update(record.custom_fields)
        
        return json.dumps(log_data, ensure_ascii=False, default=str)


class TextFormatter(logging.Formatter):
    """文字日誌格式化器"""
    
    FORMAT = (
        "%(asctime)s - %(name)s - %(levelname)s - "
        "[%(filename)s:%(lineno)d] - %(message)s"
    )
    
    def format(self, record: logging.LogRecord) -> str:
        """將日誌記錄格式化為文字"""
        # 為不同級別使用不同的顏色（可選）
        formatter = logging.Formatter(self.FORMAT)
        return formatter.format(record)


# ============================================================================
# 日誌配置函數
# ============================================================================

def _ensure_log_directory():
    """確保日誌目錄存在"""
    if LOG_FILE:
        log_dir = os.path.dirname(LOG_FILE)
        if log_dir and not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir, exist_ok=True)
            except Exception as e:
                print(f"無法建立日誌目錄 {log_dir}: {e}")


def configure_logging(
    level: str = LOG_LEVEL,
    log_format: str = LOG_FORMAT,
    log_file: Optional[str] = LOG_FILE
) -> None:
    """
    配置全域日誌系統
    
    【參數】
    level: 日誌級別 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    log_format: 日誌格式 (text, json)
    log_file: 日誌檔案路徑（不輸出檔案則為 None）
    
    【範例】
    configure_logging(level="DEBUG", log_format="json")
    """
    is_pytest = "PYTEST_CURRENT_TEST" in os.environ or any("pytest" in arg for arg in sys.argv)
    if is_pytest:
        log_file = None

    # 確保日誌目錄存在
    if log_file:
        _ensure_log_directory()
    
    # 取得根日誌記錄器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # 移除現有處理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        handler.close()
    
    # 選擇格式化器
    if log_format.lower() == "json":
        formatter = StructuredFormatter()
    else:
        formatter = TextFormatter()
    
    # 1. 控制台處理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 2. 檔案處理器（若指定）
    if log_file:
        try:
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=LOG_MAX_BYTES,
                backupCount=LOG_BACKUP_COUNT,
                encoding="utf-8"
            )
            file_handler.setLevel(getattr(logging, level.upper()))
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            root_logger.warning(f"無法設置檔案日誌處理器: {e}")
    
    root_logger.info(f"日誌配置完成: level={level}, format={log_format}, file={log_file}")


def get_logger(name: str) -> logging.Logger:
    """
    取得日誌記錄器
    
    【使用方式】
    logger = get_logger(__name__)
    logger.info("This is an info message")
    logger.error("This is an error message")
    """
    return logging.getLogger(name)


def log_with_context(logger: logging.Logger, level: str, message: str, **kwargs):
    """
    添加自定義欄位的日誌記錄
    
    【使用方式】
    log_with_context(logger, "info", "User action", user_id=123, action="upload")
    """
    extra = {"custom_fields": kwargs} if kwargs else {}
    getattr(logger, level.lower())(message, extra=extra)


# ============================================================================
# 為常見模組預配置日誌
# ============================================================================

def setup_module_loggers():
    """為常見模組設置日誌記錄器"""
    modules = [
        "app.main",
        "app.database",
        "app.models",
        "app.storage",
        "app.security",
        "app.cache",
        "app.annotation",
    ]
    
    for module_name in modules:
        logger = get_logger(module_name)
        logger.setLevel(getattr(logging, LOG_LEVEL))


# 應用程式啟動時自動配置
try:
    configure_logging()
    setup_module_loggers()
except Exception as e:
    print(f"日誌配置失敗: {e}")


# ============================================================================
# 日誌統計和監控
# ============================================================================

class LogStats:
    """日誌統計"""
    _counts = {
        "DEBUG": 0,
        "INFO": 0,
        "WARNING": 0,
        "ERROR": 0,
        "CRITICAL": 0,
    }
    
    @classmethod
    def record(cls, level: str):
        """記錄日誌"""
        if level in cls._counts:
            cls._counts[level] += 1
    
    @classmethod
    def get_stats(cls) -> dict:
        """取得統計"""
        return cls._counts.copy()
    
    @classmethod
    def reset(cls):
        """重設統計"""
        for key in cls._counts:
            cls._counts[key] = 0


# 設置日誌處理器統計
class StatsHandler(logging.Handler):
    """統計日誌級別的處理器"""
    
    def emit(self, record):
        LogStats.record(record.levelname)


if __name__ == "__main__":
    # 測試日誌配置
    logger = get_logger(__name__)
    
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    # 測試帶自定義欄位的日誌
    log_with_context(
        logger,
        "info",
        "User login",
        user_id=123,
        username="testuser",
        ip_address="192.168.1.1"
    )
