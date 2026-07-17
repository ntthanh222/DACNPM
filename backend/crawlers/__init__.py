"""Crawler modules for different news sources."""

from .base import BaseCrawler
from .config_driven import ConfigDrivenCrawler
from .registry import CrawlerRegistry, registry

__all__ = [
    'BaseCrawler',
    'ConfigDrivenCrawler',
    'CrawlerRegistry',
    'registry',
]
