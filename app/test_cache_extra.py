"""
Extra tests for cache helpers.
"""

import json
import sys
import types

from app import cache


def test_init_redis_success(monkeypatch):
    class FakeRedisClient:
        def __init__(self):
            self.ping_called = False

        def ping(self):
            self.ping_called = True

    fake_client = FakeRedisClient()

    redis_module = types.ModuleType("redis")
    redis_module.from_url = lambda *args, **kwargs: fake_client

    monkeypatch.setitem(sys.modules, "redis", redis_module)
    monkeypatch.setattr(cache, "_redis_client", None)
    monkeypatch.setattr(cache, "REDIS_AVAILABLE", False)

    cache.init_redis()
    assert cache.REDIS_AVAILABLE is True
    assert cache._redis_client is fake_client


def test_cache_manager_operations(monkeypatch):
    class FakeRedis:
        def __init__(self):
            self.store = {"key": json.dumps({"a": 1})}

        def get(self, key):
            return self.store.get(key)

        def setex(self, key, ttl, value):
            self.store[key] = value

        def delete(self, *keys):
            count = 0
            for key in keys:
                if key in self.store:
                    del self.store[key]
                    count += 1
            return count

        def keys(self, pattern):
            return list(self.store.keys())

    client = FakeRedis()
    monkeypatch.setattr(cache, "_redis_client", client)
    monkeypatch.setattr(cache, "REDIS_AVAILABLE", True)

    assert cache.CacheManager.get("key") == {"a": 1}
    assert cache.CacheManager.set("k2", {"b": 2}, ttl=10) is True
    assert cache.CacheManager.delete("k2") is True
    assert cache.CacheManager.delete_pattern("*") >= 0


def test_cache_manager_exceptions(monkeypatch):
    class ErrorRedis:
        def get(self, key):
            raise RuntimeError("fail")

        def setex(self, key, ttl, value):
            raise RuntimeError("fail")

        def delete(self, *keys):
            raise RuntimeError("fail")

        def keys(self, pattern):
            raise RuntimeError("fail")

    client = ErrorRedis()
    monkeypatch.setattr(cache, "_redis_client", client)
    monkeypatch.setattr(cache, "REDIS_AVAILABLE", True)

    assert cache.CacheManager.get("missing") is None
    assert cache.CacheManager.set("k", {"x": 1}) is False
    assert cache.CacheManager.delete("k") is False
    assert cache.CacheManager.delete_pattern("*") == 0
