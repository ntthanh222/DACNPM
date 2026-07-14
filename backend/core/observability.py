"""Shared application observability primitives."""

import time
from collections import defaultdict

from slowapi import Limiter
from slowapi.util import get_remote_address


limiter = Limiter(key_func=get_remote_address)
REQUEST_COUNT = defaultdict(int)
REQUEST_LATENCY_SECONDS = defaultdict(float)
APP_START_TIME = time.monotonic()


def record_request(method: str, path: str, status_code: int, elapsed: float) -> None:
    labels = (method, path, str(status_code))
    REQUEST_COUNT[labels] += 1
    REQUEST_LATENCY_SECONDS[labels] += elapsed


def render_metrics() -> str:
    lines = [
        "# HELP cybersec_app_uptime_seconds Application uptime in seconds.",
        "# TYPE cybersec_app_uptime_seconds gauge",
        f"cybersec_app_uptime_seconds {time.monotonic() - APP_START_TIME:.6f}",
        "# HELP cybersec_http_requests_total Total HTTP requests.",
        "# TYPE cybersec_http_requests_total counter",
    ]
    for (method, path, status), count in sorted(REQUEST_COUNT.items()):
        lines.append(
            f'cybersec_http_requests_total{{method="{method}",path="{path}",status="{status}"}} {count}'
        )
    lines.extend([
        "# HELP cybersec_http_request_duration_seconds_total Total HTTP request duration in seconds.",
        "# TYPE cybersec_http_request_duration_seconds_total counter",
    ])
    for (method, path, status), total_seconds in sorted(REQUEST_LATENCY_SECONDS.items()):
        lines.append(
            f'cybersec_http_request_duration_seconds_total{{method="{method}",path="{path}",status="{status}"}} {total_seconds:.6f}'
        )
    return "\n".join(lines) + "\n"
