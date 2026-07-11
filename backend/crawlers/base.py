"""Base crawler class for security news sources."""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

import sys
import os
# Add parent directory to path for utils imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logging_setup import get_logger
from utils.retry import RetryConfig, retry_on_failure


class BaseCrawler(ABC):
    """Abstract base class for security news crawlers."""

    def __init__(
        self,
        headless: bool = False,
        timeout: int = 10,
        page_load_delay: int = 2,
        retry_config: Optional[RetryConfig] = None
    ):
        """
        Initialize the base crawler.

        Args:
            headless: Run browser in headless mode
            timeout: Page load timeout in seconds
            page_load_delay: Additional delay after page load in seconds
            retry_config: Retry configuration
        """
        self.headless = headless
        self.timeout = timeout
        self.page_load_delay = page_load_delay
        self.retry_config = retry_config or RetryConfig()
        self.logger = get_logger(self.__class__.__name__)
        self.driver = None
        self.news_articles = []

        # Source-specific configuration to be set by subclasses
        self.source_name = None
        self.base_url = None
        self.target_url = None

    def init_driver(self) -> webdriver.Chrome:
        """
        Initialize Chrome WebDriver.

        Returns:
            Configured Chrome WebDriver instance
        """
        chrome_options = Options()

        if self.headless:
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-software-rasterizer')
            # Disable WebRTC to fix STUN server resolution errors
            chrome_options.add_argument('--disable-webrtc')
            chrome_options.add_argument('--force-webrtc-ip-handling-policy=disable_non_proxied_udp')

        # Additional options for better performance
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--window-size=1920,1080')

        # Initialize driver
        service = Service()
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # Set page load timeout
        driver.set_page_load_timeout(self.timeout)

        return driver

    @abstractmethod
    def crawl(self, max_articles: int = 10) -> List[Dict]:
        """
        Crawl articles from the news source.

        Args:
            max_articles: Maximum number of articles to crawl

        Returns:
            List of article dictionaries
        """
        pass

    @abstractmethod
    def _parse_article(self, element, index: int) -> Optional[Dict]:
        """
        Parse a single article element.

        Args:
            element: Selenium WebElement for the article
            index: Article index

        Returns:
            Dictionary with article data or None if parsing fails
        """
        pass

    @abstractmethod
    def _parse_date(self, date_text: str) -> datetime:
        """
        Parse date string to datetime object.

        Args:
            date_text: Date string from the website

        Returns:
            Datetime object
        """
        pass

    def navigate_to_page(self) -> bool:
        """
        Navigate to the target page.

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Navigating to {self.target_url}")
            self.driver.get(self.target_url)

            # Wait for page to load
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            self.logger.info("Page loaded successfully")
            return True

        except TimeoutException:
            self.logger.error("Timeout while waiting for page to load")
            return False
        except Exception as e:
            self.logger.error(f"Error navigating to page: {e}")
            return False

    def find_articles(self, css_selector: str) -> List:
        """
        Find article elements using CSS selector.

        Args:
            css_selector: CSS selector for article containers

        Returns:
            List of WebElement objects
        """
        import time
        time.sleep(self.page_load_delay)

        try:
            article_elements = self.driver.find_elements(By.CSS_SELECTOR, css_selector)
            self.logger.info(f"Found {len(article_elements)} article containers")
            return article_elements
        except Exception as e:
            self.logger.error(f"Error finding articles: {e}")
            return []

    def parse_articles(self, article_elements: List, max_articles: int, css_selector: str) -> int:
        """
        Parse multiple articles from elements.

        Args:
            article_elements: List of WebElement objects
            max_articles: Maximum number of articles to parse
            css_selector: CSS selector for parsing (for logging)

        Returns:
            Number of successfully parsed articles
        """
        parsed_count = 0

        for idx, article in enumerate(article_elements[:max_articles], 1):
            try:
                article_data = self._parse_article(article, idx)
                if article_data:
                    self.news_articles.append(article_data)
                    parsed_count += 1
                    self.logger.debug(f"Parsed article {idx}/{max_articles}: {article_data['title'][:50]}...")
            except Exception as e:
                self.logger.warning(f"Error parsing article {idx}: {e}")
                continue

        self.logger.info(f"Successfully parsed {parsed_count} articles")
        return parsed_count

    def cleanup(self):
        """Clean up resources."""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("WebDriver closed")
            except Exception as e:
                self.logger.warning(f"Error closing WebDriver: {e}")
            finally:
                self.driver = None

    def __enter__(self):
        """Context manager entry."""
        self.driver = self.init_driver()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()
