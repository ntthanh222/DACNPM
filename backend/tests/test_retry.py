import pytest

from backend.utils import retry


def test_retry_returns_on_first_success(monkeypatch):
    sleeps = []
    monkeypatch.setattr(retry.time, "sleep", sleeps.append)

    @retry.retry_on_failure(max_attempts=3, initial_delay=2)
    def operation():
        return "done"

    assert operation() == "done"
    assert sleeps == []


def test_retry_uses_exponential_delays_before_eventual_success(monkeypatch):
    sleeps, attempts = [], []
    monkeypatch.setattr(retry.time, "sleep", sleeps.append)

    @retry.retry_on_failure(max_attempts=3, initial_delay=0.5, backoff_multiplier=2, exceptions=(ValueError,))
    def operation():
        attempts.append(1)
        if len(attempts) < 3:
            raise ValueError("transient")
        return "done"

    assert operation() == "done"
    assert len(attempts) == 3
    assert sleeps == [0.5, 1.0]


def test_retry_reraises_last_expected_exception(monkeypatch):
    monkeypatch.setattr(retry.time, "sleep", lambda _delay: None)

    @retry.retry_on_failure(max_attempts=2, exceptions=(ValueError,))
    def operation():
        raise ValueError("permanent")

    with pytest.raises(ValueError, match="permanent"):
        operation()


def test_retry_config_calculates_bounded_delays_and_loads_dict():
    config = retry.RetryConfig.from_dict({"max_attempts": 5, "initial_delay": 2, "backoff_multiplier": 3, "max_delay": 10})

    assert config.max_attempts == 5
    assert config.get_delay(1) == 0
    assert config.get_delay(2) == 6
    assert config.get_delay(4) == 10
