"""
Redis 快取層模組

【功能】
提供 Redis 連線池和快取管理工具

【特性】
- 連線池管理
- 自動序列化/反序列化 (JSON)
- 過期時間管理
- 優雅降級（Redis 不可用時降級到無快取模式）

【環境變數】
- REDIS_URL: Redis 連線字串 (預設: redis://localhost:6379/0)
- CACHE_TTL: 預設快取 TTL 秒數 (預設: 3600)
"""

import os
import json
import logging
from typing import Optional, Any, Dict
from functools import wraps
import asyncio

logger = logging.getLogger(__name__)

# Redis 配置
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DEFAULT_TTL = int(os.getenv("CACHE_TTL", "3600"))

# Redis 連線池（全域單例）
_redis_client = None
REDIS_AVAILABLE = False


def init_redis():
    """初始化 Redis 連線"""
    global _redis_client, REDIS_AVAILABLE
    try:
        import redis
        _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        # 測試連線
        _redis_client.ping()
        REDIS_AVAILABLE = True
        logger.info(f"✓ Redis 連線成功: {REDIS_URL}")
    except Exception as e:
        logger.warning(f"✗ Redis 連線失敗: {e}，將以無快取模式運行")
        REDIS_AVAILABLE = False


def get_redis():
    """取得 Redis 客戶端"""
    global _redis_client
    if _redis_client is None:
        init_redis()
    return _redis_client


class CacheManager:
    """快取管理器"""
    
    @staticmethod
    def get_cache_key(*args: str) -> str:
        """生成快取鍵"""
        return ":".join(str(arg) for arg in args)
    
    @staticmethod
    def get(key: str) -> Optional[Any]:
        """從快取中取得值"""
        if not REDIS_AVAILABLE:
            return None
        
        try:
            redis_client = get_redis()
            value = redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning(f"快取讀取失敗 ({key}): {e}")
            return None
    
    @staticmethod
    def set(key: str, value: Any, ttl: int = DEFAULT_TTL) -> bool:
        """設定快取"""
        if not REDIS_AVAILABLE:
            return False
        
        try:
            redis_client = get_redis()
            redis_client.setex(key, ttl, json.dumps(value, default=str))
            return True
        except Exception as e:
            logger.warning(f"快取寫入失敗 ({key}): {e}")
            return False
    
    @staticmethod
    def delete(key: str) -> bool:
        """刪除快取"""
        if not REDIS_AVAILABLE:
            return False
        
        try:
            redis_client = get_redis()
            redis_client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"快取刪除失敗 ({key}): {e}")
            return False
    
    @staticmethod
    def delete_pattern(pattern: str) -> int:
        """刪除匹配模式的所有快取"""
        if not REDIS_AVAILABLE:
            return 0
        
        try:
            redis_client = get_redis()
            keys = redis_client.keys(pattern)
            if keys:
                return redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"快取批量刪除失敗 ({pattern}): {e}")
            return 0


def cache_result(ttl: int = DEFAULT_TTL, key_prefix: str = ""):
    """快取結果裝飾器
    
    使用範例：
    @cache_result(ttl=3600, key_prefix="file_list")
    def get_files(user_id: int):
        return db.query(File).filter(File.user_id == user_id).all()
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成快取鍵
            cache_key = CacheManager.get_cache_key(
                key_prefix or func.__name__,
                *[str(arg) for arg in args],
                *[f"{k}={v}" for k, v in kwargs.items()]
            )
            
            # 嘗試從快取取得
            cached_value = CacheManager.get(cache_key)
            if cached_value is not None:
                logger.debug(f"快取命中: {cache_key}")
                return cached_value
            
            # 執行函式
            result = func(*args, **kwargs)
            
            # 寫入快取
            CacheManager.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator


# 初始化 Redis 連線
init_redis()
