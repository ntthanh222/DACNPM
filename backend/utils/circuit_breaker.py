"""
Circuit Breaker Pattern for CyberSec Assistant

Protects against cascading failures when external APIs fail.
Implements the circuit breaker pattern for VirusTotal, NIST NVD, and HaveIBeenPwned.
"""

import asyncio
import time
import logging
from typing import Callable, Optional, Any, Dict
from fastapi import HTTPException
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"           # Normal operation, requests pass through
    OPEN = "open"               # Circuit is open, requests fail immediately
    HALF_OPEN = "half_open"     # Testing if service has recovered


class CircuitBreakerOpenError(HTTPException):
    """Exception raised when circuit breaker is open."""
    def __init__(self, service_name: str, retry_after: int):
        super().__init__(
            status_code=503,
            detail={
                "error": f"Service temporarily unavailable: {service_name}",
                "message": "Too many recent failures. Circuit breaker is open to prevent cascading failures.",
                "retry_after": retry_after,
                "service": service_name
            }
        )


class CircuitBreaker:
    """
    Circuit Breaker implementation for external API protection.

    Prevents cascading failures by:
    1. Opening circuit after threshold failures
    2. Failing fast when circuit is open
    3. Testing service recovery with half-open state
    """

    def __init__(
        self,
        service_name: str,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout: int = 60,
        half_open_max_calls: int = 3
    ):
        """
        Initialize circuit breaker.

        Args:
            service_name: Name of the service being protected
            failure_threshold: Number of failures before opening circuit
            success_threshold: Number of successes needed to close circuit
            timeout: Seconds to wait before trying half-open state
            half_open_max_calls: Max test calls allowed in half-open state
        """
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.half_open_max_calls = half_open_max_calls

        # Circuit state
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.half_open_calls = 0

        # Statistics
        self.total_calls = 0
        self.total_failures = 0
        self.total_successes = 0

        # Thread safety
        self._lock = asyncio.Lock()

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker protection.

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function return value

        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: If function execution fails
        """
        async with self._lock:
            self.total_calls += 1

            # Check if circuit should transition to half-open
            if self.state == CircuitState.OPEN:
                if time.time() - self.last_failure_time > self.timeout:
                    logger.info(f"🔧 Circuit {self.service_name} transitioning to HALF_OPEN for recovery test")
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                else:
                    logger.warning(f"⚡ Circuit {self.service_name} is OPEN - failing fast")
                    raise CircuitBreakerOpenError(
                        self.service_name,
                        retry_after=int(self.timeout - (time.time() - self.last_failure_time))
                    )

        try:
            # Execute the function
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)

            # Handle success
            await self._on_success()
            return result

        except Exception as e:
            # Handle failure
            await self._on_failure()
            raise e

    async def _on_success(self):
        """Handle successful execution."""
        async with self._lock:
            self.total_successes += 1

            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                self.half_open_calls += 1
                logger.info(f"✅ Circuit {self.service_name} HALF_OPEN success: {self.success_count}/{self.success_threshold}")

                # Close circuit if success threshold reached
                if self.success_count >= self.success_threshold:
                    logger.info(f"🔒 Circuit {self.service_name} CLOSED after recovery verification")
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
                    self.half_open_calls = 0

            elif self.state == CircuitState.CLOSED:
                # Reset failure count on success in closed state
                if self.failure_count > 0:
                    self.failure_count = max(0, self.failure_count - 1)

    async def _on_failure(self):
        """Handle execution failure."""
        async with self._lock:
            self.total_failures += 1
            self.failure_count += 1
            self.last_failure_time = time.time()

            logger.error(f"❌ Circuit {self.service_name} failure: {self.failure_count}/{self.failure_threshold}")

            # Open circuit if failure threshold reached
            if self.failure_count >= self.failure_threshold:
                logger.warning(f"⚠️ Circuit {self.service_name} OPEN due to {self.failure_count} failures")
                self.state = CircuitState.OPEN
                self.success_count = 0
                self.half_open_calls = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        return {
            "service": self.service_name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "failure_threshold": self.failure_threshold,
            "success_threshold": self.success_threshold,
            "total_calls": self.total_calls,
            "total_failures": self.total_failures,
            "total_successes": self.total_successes,
            "last_failure_time": self.last_failure_time,
            "retry_after": int(self.timeout - (time.time() - (self.last_failure_time or 0))) if self.state == CircuitState.OPEN else 0
        }

    def reset(self):
        """Reset circuit breaker to initial state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.half_open_calls = 0
        logger.info(f"🔄 Circuit {self.service_name} reset to initial state")


# ============================================================================
# Circuit Breaker Instances for External APIs
# ============================================================================

# VirusTotal API Circuit Breaker
virustotal_circuit = CircuitBreaker(
    service_name="VirusTotal",
    failure_threshold=5,      # Open after 5 consecutive failures
    success_threshold=2,     # Close after 2 consecutive successes
    timeout=60,              # Wait 60 seconds before retry
    half_open_max_calls=3    # Allow 3 test calls in half-open state
)

# NIST NVD API Circuit Breaker
nist_nvd_circuit = CircuitBreaker(
    service_name="NIST NVD",
    failure_threshold=3,      # More conservative (NIST is less reliable)
    success_threshold=2,
    timeout=120,             # Wait 2 minutes (NIST rate limits)
    half_open_max_calls=2
)

# HaveIBeenPwned API Circuit Breaker
hibp_circuit = CircuitBreaker(
    service_name="HaveIBeenPwned",
    failure_threshold=5,
    success_threshold=2,
    timeout=30,              # Short timeout (HIBP is usually reliable)
    half_open_max_calls=3
)


# ============================================================================
# Convenience Functions
# ============================================================================

async def call_virustotal(func: Callable, *args, **kwargs) -> Any:
    """
    Execute VirusTotal API call with circuit breaker protection.

    Args:
        func: VirusTotal API function
        *args: Function arguments
        **kwargs: Function keyword arguments

    Returns:
        API response

    Raises:
        CircuitBreakerOpenError: If VirusTotal circuit is open
    """
    return await virustotal_circuit.call(func, *args, **kwargs)


async def call_nist_nvd(func: Callable, *args, **kwargs) -> Any:
    """
    Execute NIST NVD API call with circuit breaker protection.

    Args:
        func: NIST NVD API function
        *args: Function arguments
        **kwargs: Function keyword arguments

    Returns:
        API response

    Raises:
        CircuitBreakerOpenError: If NIST NVD circuit is open
    """
    return await nist_nvd_circuit.call(func, *args, **kwargs)


async def call_hibp(func: Callable, *args, **kwargs) -> Any:
    """
    Execute HaveIBeenPwned API call with circuit breaker protection.

    Args:
        func: HaveIBeenPwned API function
        *args: Function arguments
        **kwargs: Function keyword arguments

    Returns:
        API response

    Raises:
        CircuitBreakerOpenError: If HaveIBeenPwned circuit is open
    """
    return await hibp_circuit.call(func, *args, **kwargs)


def get_circuit_breaker_stats() -> Dict[str, Any]:
    """Get statistics for all circuit breakers."""
    return {
        "virustotal": virustotal_circuit.get_stats(),
        "nist_nvd": nist_nvd_circuit.get_stats(),
        "haveibeenpwned": hibp_circuit.get_stats()
    }


def reset_all_circuit_breakers():
    """Reset all circuit breakers to initial state."""
    virustotal_circuit.reset()
    nist_nvd_circuit.reset()
    hibp_circuit.reset()
    logger.info("🔄 All circuit breakers reset")


# ============================================================================
# Development Note
# ============================================================================

"""
PRODUCTION CONFIGURATION GUIDE:

Circuit breaker parameters should be tuned based on:

1. Service Reliability:
   - High reliability (HIBP): Lower failure_threshold, shorter timeout
   - Low reliability (NIST): Higher failure_threshold, longer timeout

2. Business Impact:
   - Critical services: Lower thresholds to fail fast
   - Non-critical services: Higher thresholds for tolerance

3. Rate Limits:
   - Set timeout > rate limit window to allow recovery
   - Consider API rate limits in timeout calculation

Example for production:
```python
# For critical services
critical_circuit = CircuitBreaker(
    service_name="PaymentAPI",
    failure_threshold=3,      # Fail fast
    success_threshold=2,
    timeout=30,              # Quick recovery
    half_open_max_calls=2
)

# For tolerant services
tolerant_circuit = CircuitBreaker(
    service_name="CacheAPI",
    failure_threshold=10,     # High tolerance
    success_threshold=3,
    timeout=120,             # Patient recovery
    half_open_max_calls=5
)
```

MONITORING RECOMMENDATIONS:
- Track circuit state transitions in logs
- Alert when circuits open repeatedly
- Monitor total_failures vs total_successes ratio
- Set up dashboards for circuit breaker stats
"""
