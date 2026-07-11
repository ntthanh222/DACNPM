import pytest

from backend.utils.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError, CircuitState


@pytest.mark.asyncio
async def test_circuit_breaker_opens_and_fails_fast_after_threshold():
    breaker = CircuitBreaker("test", failure_threshold=2, timeout=60)
    async def fail(): raise RuntimeError("down")
    with pytest.raises(RuntimeError): await breaker.call(fail)
    with pytest.raises(RuntimeError): await breaker.call(fail)
    assert breaker.state is CircuitState.OPEN
    with pytest.raises(CircuitBreakerOpenError): await breaker.call(fail)
    assert breaker.get_stats()["failure_count"] == 2


@pytest.mark.asyncio
async def test_circuit_breaker_recovers_through_half_open(monkeypatch):
    breaker = CircuitBreaker("test", failure_threshold=1, success_threshold=1, timeout=1)
    async def fail(): raise RuntimeError()
    async def succeed(): return "ok"
    with pytest.raises(RuntimeError): await breaker.call(fail)
    monkeypatch.setattr("backend.utils.circuit_breaker.time.time", lambda: breaker.last_failure_time + 2)
    assert await breaker.call(succeed) == "ok"
    assert breaker.state is CircuitState.CLOSED
    breaker.reset()
    assert breaker.get_stats()["state"] == "closed"
