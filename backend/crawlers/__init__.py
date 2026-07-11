"""Crawler modules for different news sources."""

from .base import BaseCrawler
from .thehackernews import TheHackerNewsCrawler
from .vnexpress import VnExpressCrawler
from .registry import CrawlerRegistry, registry
from .config_base_crawler import ConfigDrivenCrawler
from .config_registry import ConfigDrivenRegistry, config_registry

__all__ = [
    'BaseCrawler',
    'TheHackerNewsCrawler',
    'VnExpressCrawler',
    'CrawlerRegistry',
    'registry',
    'ConfigDrivenCrawler',
    'ConfigDrivenRegistry',
    'config_registry',
]
