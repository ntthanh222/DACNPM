"""
Configuration Loader for Crawlers

Provides centralized configuration management for all crawlers.
Loads configuration from YAML files and provides easy access.
"""

import yaml
import os
from typing import Dict, Any, Optional, List
from pathlib import Path


class CrawlerConfig:
    """
    Configuration manager for crawler settings.

    Loads and provides access to crawler configuration from YAML files.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the configuration loader.

        Args:
            config_path: Path to configuration file (optional)
        """
        if config_path is None:
            # Default path relative to this file
            config_path = os.path.join(os.path.dirname(__file__), 'crawlers.yml')

        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from YAML file.

        Returns:
            Configuration dictionary
        """
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                print(f"✅ Loaded crawler configuration from {self.config_path}")
                return config
        except FileNotFoundError:
            print(f"⚠️  Configuration file not found: {self.config_path}")
            return self._get_default_config()
        except yaml.YAMLError as e:
            print(f"⚠️  Error parsing YAML configuration: {e}")
            return self._get_default_config()
        except Exception as e:
            print(f"⚠️  Error loading configuration: {e}")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """
        Get default configuration when file loading fails.

        Returns:
            Default configuration dictionary
        """
        return {
            'global_settings': {
                'headless': False,
                'timeout': 10,
                'page_load_delay': 2,
                'max_retries': 3,
                'retry_delay': 2
            },
            'thehackernews': {
                'enabled': True,
                'max_articles': 10,
                'base_url': 'https://thehackernews.com',
                'target_url': 'https://thehackernews.com/',
                'source_name': 'The Hacker News',
                'selectors': {
                    'article_container': 'a.latest-link, article, .latest-link',
                    'title': 'h2, h3, h1, .title, .post-title, .entry-title',
                    'description': 'p, .excerpt, .summary, .post-excerpt, .entry-summary',
                    'date': 'time, .date, .published, .post-date, .entry-date, span[class*="date"]'
                },
                'date_formats': ['%b %d, %Y %H:%M %Z'],
                'url_patterns': ['thehackernews.com']
            }
        }

    def get_global_setting(self, setting_name: str, default: Any = None) -> Any:
        """
        Get a global setting value.

        Args:
            setting_name: Name of the setting
            default: Default value if setting not found

        Returns:
            Setting value or default
        """
        return self.config.get('global_settings', {}).get(setting_name, default)

    def get_crawler_config(self, crawler_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific crawler.

        Args:
            crawler_name: Name of the crawler

        Returns:
            Crawler configuration dictionary
        """
        crawler_config = self.config.get(crawler_name, {})

        if not crawler_config:
            print(f"⚠️  No configuration found for crawler '{crawler_name}'")

        return crawler_config

    def is_crawler_enabled(self, crawler_name: str) -> bool:
        """
        Check if a crawler is enabled.

        Args:
            crawler_name: Name of the crawler

        Returns:
            True if enabled, False otherwise
        """
        crawler_config = self.get_crawler_config(crawler_name)
        return crawler_config.get('enabled', False)

    def get_selectors(self, crawler_name: str) -> Dict[str, str]:
        """
        Get CSS selectors for a crawler.

        Args:
            crawler_name: Name of the crawler

        Returns:
            Dictionary of CSS selectors
        """
        crawler_config = self.get_crawler_config(crawler_name)
        return crawler_config.get('selectors', {})

    def get_date_formats(self, crawler_name: str) -> List[str]:
        """
        Get date formats for a crawler.

        Args:
            crawler_name: Name of the crawler

        Returns:
            List of date format strings
        """
        crawler_config = self.get_crawler_config(crawler_name)
        return crawler_config.get('date_formats', ['%Y-%m-%d'])

    def get_max_articles(self, crawler_name: str) -> int:
        """
        Get max articles setting for a crawler.

        Args:
            crawler_name: Name of the crawler

        Returns:
            Maximum number of articles to crawl
        """
        crawler_config = self.get_crawler_config(crawler_name)
        return crawler_config.get('max_articles', 10)

    def get_source_name(self, crawler_name: str) -> str:
        """
        Get source name for a crawler.

        Args:
            crawler_name: Name of the crawler

        Returns:
            Source name
        """
        crawler_config = self.get_crawler_config(crawler_name)
        return crawler_config.get('source_name', crawler_name.title())

    def get_urls(self, crawler_name: str) -> tuple:
        """
        Get base and target URLs for a crawler.

        Args:
            crawler_name: Name of the crawler

        Returns:
            Tuple of (base_url, target_url)
        """
        crawler_config = self.get_crawler_config(crawler_name)
        base_url = crawler_config.get('base_url', '')
        target_url = crawler_config.get('target_url', base_url)
        return base_url, target_url

    def list_enabled_crawlers(self) -> List[str]:
        """
        Get list of enabled crawler names.

        Returns:
            List of enabled crawler names
        """
        enabled = []
        for crawler_name, crawler_config in self.config.items():
            if crawler_name == 'global_settings':
                continue
            if crawler_config.get('enabled', False):
                enabled.append(crawler_name)
        return enabled

    def list_all_crawlers(self) -> List[str]:
        """
        Get list of all configured crawler names.

        Returns:
            List of all crawler names
        """
        all_crawlers = []
        for crawler_name in self.config.keys():
            if crawler_name == 'global_settings':
                continue
            all_crawlers.append(crawler_name)
        return all_crawlers


# Global configuration instance
crawler_config = CrawlerConfig()