"""
Configuration Management

Centralized configuration loading and management for the application.
"""

from .config_loader import CrawlerConfig, crawler_config
from .settings import settings, Settings

__all__ = ['CrawlerConfig', 'crawler_config', 'settings', 'Settings']