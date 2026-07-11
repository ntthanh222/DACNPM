import pytest
from fastapi import HTTPException

from backend.utils import rate_limiter


@pytest.mark.asyncio
async def test_sse_tracker_limits_connections_and_cleans_expired_entries(monkeypatch):
    tracker = rate_limiter.SSEConnectionTracker(max_connections_per_user=2, connection_timeout=5)
    monkeypatch.setattr(rate_limiter.time, "time", lambda: 100)

    assert await tracker.increment_connection("user") == 1
    assert await tracker.increment_connection("user") == 2
    with pytest.raises(HTTPException) as error:
        await tracker.increment_connection("user")
    assert error.value.status_code == 429
    assert await tracker.decrement_connection("user") == 1
    tracker._connections["expired"] = {"count": 1, "last_seen": 90}
    tracker._cleanup_expired_connections(100)
    assert "expired" not in tracker._connections
    assert await tracker.decrement_connection("user") == 0


@pytest.mark.asyncio
async def test_rate_limiter_enforces_window_then_allows_expired_request(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr(rate_limiter.time, "time", lambda: clock[0])
    limiter = rate_limiter.RateLimiter(requests_per_minute=2, window_size=10)

    assert await limiter.check_rate_limit("ip") is True
    assert await limiter.check_rate_limit("ip") is True
    with pytest.raises(HTTPException) as error:
        await limiter.check_rate_limit("ip")
    assert error.value.status_code == 429
    clock[0] = 111.0
    assert await limiter.check_rate_limit("ip") is True
    assert limiter.get_stats()["total_tracked_requests"] == 1


@pytest.mark.asyncio
async def test_rate_limiter_convenience_functions_delegate_to_global_instances(monkeypatch):
    class Tracker:
        async def increment_connection(self, user_id): return 2
        async def decrement_connection(self, user_id): return 1
        def get_stats(self): return {"tracker": True}

    class Limiter:
        async def check_rate_limit(self, identifier): return True
        def get_stats(self): return {"limiter": True}

    monkeypatch.setattr(rate_limiter, "sse_tracker", Tracker())
    monkeypatch.setattr(rate_limiter, "api_rate_limiter", Limiter())
    assert await rate_limiter.check_sse_limit("u") == 2
    assert await rate_limiter.release_sse_connection("u") == 1
    assert await rate_limiter.check_api_rate_limit("u") is True
    assert rate_limiter.get_sse_stats() == {"tracker": True}
    assert rate_limiter.get_rate_limiter_stats() == {"limiter": True}
