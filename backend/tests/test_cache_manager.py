import pytest

from backend.utils import cache_manager


class FakeRedis:
    def __init__(self): self.values = {}; self.deleted = []
    def get(self, key): return self.values.get(key)
    def setex(self, key, ttl, value): self.values[key] = value
    def delete(self, *keys):
        self.deleted.extend(keys)
        for key in keys: self.values.pop(key, None)
        return len(keys)
    def keys(self, _pattern): return list(self.values)
    def info(self, _section): return {"keyspace_hits": 3, "keyspace_misses": 1, "total_connections_received": 2, "total_commands_processed": 4, "used_memory_human": "1M"}
    def dbsize(self): return len(self.values)


@pytest.mark.asyncio
async def test_cache_read_write_invalidation_and_stats(monkeypatch):
    client = FakeRedis()
    monkeypatch.setattr(cache_manager, "get_redis_client", lambda: client)
    assert await cache_manager.set_cached_data("key", {"value": 1}) is True
    assert await cache_manager.get_cached_data("key") == {"value": 1}
    assert await cache_manager.invalidate_pattern("*") == 1
    assert await cache_manager.get_cached_data("key") is None
    assert await cache_manager.invalidate_cache("missing") is True
    assert (await cache_manager.get_cache_stats())["cache_hit_rate"] == "75.0%"


@pytest.mark.asyncio
async def test_cache_handles_unavailable_and_computes_only_when_needed(monkeypatch):
    monkeypatch.setattr(cache_manager, "get_redis_client", lambda: None)
    assert await cache_manager.get_cached_data("key") is None
    assert await cache_manager.set_cached_data("key", {}) is False
    calls = []
    async def compute(): calls.append(1); return {"fresh": True}
    async def cache_miss(*_args):
        return None
    monkeypatch.setattr(cache_manager, "get_cached_data", cache_miss)
    result = await cache_manager.get_or_compute("key", compute)
    assert result == {"fresh": True}
    assert calls == [1]
    assert cache_manager.calculate_hit_rate({}) == "0.0%"


@pytest.mark.asyncio
async def test_cache_convenience_functions_build_expected_keys(monkeypatch):
    calls = []
    async def fake_get_or_compute(*args): calls.append(args); return {"ok": True}
    async def fake_invalidate(pattern): return 1
    monkeypatch.setattr(cache_manager, "get_or_compute", fake_get_or_compute)
    monkeypatch.setattr(cache_manager, "invalidate_pattern", fake_invalidate)
    async def compute(): return {}
    assert await cache_manager.get_dashboard_stats("user", compute) == {"ok": True}
    assert await cache_manager.get_admin_stats(compute) == {"ok": True}
    assert await cache_manager.invalidate_user_cache("user") is True
    assert calls[0][0] == "dashboard_stats:user"
    assert calls[1][0] == "admin_stats:global"
