"""Retry mechanism with exponential backoff for crawler operations."""

import time
from functools import wraps
from typing import Callable, Any, Optional, Tuple
try:
    from selenium.common.exceptions import TimeoutException, WebDriverException
    _has_selenium = True
except ImportError:
    _has_selenium = False


def retry_on_failure(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_multiplier: float = 2.0,
    exceptions: Optional[Tuple] = None
) -> Callable:
    """
    Decorator to retry a function on failure with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay in seconds before first retry
        backoff_multiplier: Multiplier for exponential backoff
        exceptions: Tuple of exceptions to catch and retry

    Returns:
        Decorated function with retry logic

    Example:
        @retry_on_failure(max_attempts=3, initial_delay=1.0, backoff_multiplier=2.0)
        def fetch_page(url):
            driver.get(url)
            return driver.page_source
    """
    if exceptions is None:
        if _has_selenium:
            exceptions = (TimeoutException, WebDriverException, Exception)
        else:
            exceptions = (Exception,)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            delay = initial_delay

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt < max_attempts:
                        time.sleep(delay)
                        delay *= backoff_multiplier
                    else:
                        raise last_exception

        return wrapper
    return decorator


class RetryConfig:
    """Configuration for retry mechanism."""

    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        backoff_multiplier: float = 2.0,
        max_delay: float = 60.0
    ):
        """
        Initialize retry configuration.

        Args:
            max_attempts: Maximum number of retry attempts
            initial_delay: Initial delay in seconds
            backoff_multiplier: Multiplier for exponential backoff
            max_delay: Maximum delay between retries in seconds
        """
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.backoff_multiplier = backoff_multiplier
        self.max_delay = max_delay

    def get_delay(self, attempt: int) -> float:
        """
        Calculate delay for a given attempt using exponential backoff.

        Args:
            attempt: Current attempt number (1-indexed)

        Returns:
            Delay in seconds
        """
        if attempt <= 1:
            return 0

        delay = self.initial_delay * (self.backoff_multiplier ** (attempt - 1))
        return min(delay, self.max_delay)

    @classmethod
    def from_dict(cls, config_dict: dict) -> 'RetryConfig':
        """
        Create RetryConfig from dictionary.

        Args:
            config_dict: Dictionary with retry configuration

        Returns:
            RetryConfig instance
        """
        return cls(
            max_attempts=config_dict.get('max_attempts', 3),
            initial_delay=config_dict.get('initial_delay', 1.0),
            backoff_multiplier=config_dict.get('backoff_multiplier', 2.0),
            max_delay=config_dict.get('max_delay', 60.0)
        )
