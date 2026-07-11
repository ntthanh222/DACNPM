"""Crawler registry for managing different news source crawlers."""

import sys
import os
# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, Type, Optional, List
from .base import BaseCrawler
from .thehackernews import TheHackerNewsCrawler
from .vnexpress import VnExpressCrawler
from .securityweek import SecurityWeekCrawler
from .krebsonsecurity import KrebsOnSecurityCrawler
from .bleepingcomputer import BleepingComputerCrawler
from .darkreading import DarkReadingCrawler
from .helpnetsecurity import HelpNetSecurityCrawler
from .theregister import TheRegisterCrawler

from utils.logging_setup import get_logger


class CrawlerRegistry:
    """Registry for managing and instantiating crawlers."""

    def __init__(self):
        """Initialize the crawler registry."""
        self.logger = get_logger('CrawlerRegistry')
        self._crawlers: Dict[str, Type[BaseCrawler]] = {
            'thehackernews': TheHackerNewsCrawler,
            'vnexpress': VnExpressCrawler,
            'securityweek': SecurityWeekCrawler,
            'krebsonsecurity': KrebsOnSecurityCrawler,
            'bleepingcomputer': BleepingComputerCrawler,
            'darkreading': DarkReadingCrawler,
            'helpnetsecurity': HelpNetSecurityCrawler,
            'theregister': TheRegisterCrawler,
        }

    def register(self, name: str, crawler_class: Type[BaseCrawler]):
        """
        Register a new crawler.

        Args:
            name: Unique name for the crawler
            crawler_class: Crawler class to register
        """
        if name in self._crawlers:
            self.logger.warning(f"Crawler '{name}' already registered, overwriting")

        self._crawlers[name] = crawler_class
        self.logger.info(f"Registered crawler: {name}")

    def unregister(self, name: str) -> bool:
        """
        Unregister a crawler.

        Args:
            name: Name of the crawler to unregister

        Returns:
            True if crawler was unregistered, False if not found
        """
        if name in self._crawlers:
            del self._crawlers[name]
            self.logger.info(f"Unregistered crawler: {name}")
            return True

        self.logger.warning(f"Crawler '{name}' not found")
        return False

    def get_crawler(self, name: str, **kwargs) -> Optional[BaseCrawler]:
        """
        Get an instance of a registered crawler.

        Args:
            name: Name of the crawler
            **kwargs: Arguments to pass to crawler constructor

        Returns:
            Crawler instance or None if not found
        """
        if name not in self._crawlers:
            self.logger.error(f"Crawler '{name}' not registered")
            return None

        try:
            crawler_class = self._crawlers[name]
            return crawler_class(**kwargs)
        except Exception as e:
            self.logger.error(f"Error instantiating crawler '{name}': {e}")
            return None

    def list_crawlers(self) -> List[str]:
        """
        Get list of registered crawler names.

        Returns:
            List of crawler names
        """
        return list(self._crawlers.keys())

    def is_registered(self, name: str) -> bool:
        """
        Check if a crawler is registered.

        Args:
            name: Name of the crawler

        Returns:
            True if registered, False otherwise
        """
        return name in self._crawlers

    def create_crawlers(
        self,
        sources: Optional[List[str]] = None,
        enabled_sources: Optional[Dict[str, bool]] = None,
        headless: bool = False,
        timeout: int = 10,
        page_load_delay: int = 2
    ) -> Dict[str, BaseCrawler]:
        """
        Create multiple crawler instances.

        Args:
            sources: List of source names to create crawlers for (None for all)
            enabled_sources: Dictionary of source names and their enabled status
            headless: Run browsers in headless mode
            timeout: Page load timeout in seconds
            page_load_delay: Additional delay after page load in seconds

        Returns:
            Dictionary of crawler instances
        """
        crawlers = {}

        # Determine which sources to create crawlers for
        if sources is None:
            sources = self.list_crawlers()

        for source_name in sources:
            # Check if source is enabled
            if enabled_sources and not enabled_sources.get(source_name, True):
                self.logger.debug(f"Source '{source_name}' is disabled, skipping")
                continue

            # Create crawler instance
            crawler = self.get_crawler(
                source_name,
                headless=headless,
                timeout=timeout,
                page_load_delay=page_load_delay
            )

            if crawler:
                crawlers[source_name] = crawler

        self.logger.info(f"Created {len(crawlers)} crawler instances")
        return crawlers


# Global registry instance
registry = CrawlerRegistry()
