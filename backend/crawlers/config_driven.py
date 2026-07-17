"""Configuration-driven security news crawler.

The repository keeps source selectors in ``backend/config/crawlers.yml``.
Using one implementation here prevents the registry from depending on
source modules that are not part of the checkout.
"""

import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import yaml
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, WebDriverException

from .base import BaseCrawler

logger = logging.getLogger(__name__)


class ConfigDrivenCrawler(BaseCrawler):
    """Crawl a source using selectors and metadata from the YAML config."""

    def __init__(self, source_name: str, **kwargs: Any):
        super().__init__(**kwargs)
        self.source_key = source_name
        config_path = Path(__file__).parents[1] / "config" / "crawlers.yml"
        
        if not config_path.exists():
            raise FileNotFoundError(f"Crawler config not found at {config_path}")
            
        with config_path.open(encoding="utf-8") as handle:
            config = yaml.safe_load(handle) or {}
            
        source = config.get(source_name)
        if not source:
            raise ValueError(f"Source '{source_name}' not found in crawler config")
            
        self.source_name = source.get("source_name", source_name)
        self.base_url = source.get("base_url")
        self.target_url = source.get("target_url", self.base_url)
        self.selectors: Dict[str, str] = source.get("selectors", {})
        self.date_formats: List[str] = source.get("date_formats", [])
        
        # Validation
        self._validate_config()

    def _validate_config(self):
        if not self.base_url or not self.target_url:
            raise ValueError("base_url and target_url are required")
            
        for url in [self.base_url, self.target_url]:
            parsed = urlparse(url)
            if parsed.scheme not in ["http", "https"]:
                raise ValueError(f"Invalid URL scheme in {url}")
                
        if not self.selectors.get("article_container"):
            raise ValueError("article_container selector is required")
            
        if not self.selectors.get("title"):
            raise ValueError("title selector is required")
            
        if not isinstance(self.date_formats, list):
            raise ValueError("date_formats must be a list")

    def _text(self, element: Any, selector: Optional[str]) -> str:
        if not selector:
            return ""
        try:
            return element.find_element(By.CSS_SELECTOR, selector).text.strip()
        except NoSuchElementException:
            return ""
        except Exception as e:
            logger.warning(f"Error extracting text with selector '{selector}': {e}")
            return ""

    def _attribute(self, element: Any, selector: Optional[str], name: str) -> str:
        if not selector:
            return ""
        try:
            node = element.find_element(By.CSS_SELECTOR, selector)
            return (node.get_attribute(name) or "").strip()
        except NoSuchElementException:
            return ""
        except Exception as e:
            logger.warning(f"Error extracting attribute '{name}' with selector '{selector}': {e}")
            return ""

    def _parse_article(self, element: Any, index: int) -> Optional[Dict[str, Any]]:
        title = self._text(element, self.selectors.get("title"))
        url = self._attribute(element, self.selectors.get("title"), "href")
        
        if not url:
            url = self._attribute(element, self.selectors.get("article_container"), "href")
            
        if not title or not url:
            return None
            
        # Clean URL
        url = urljoin(self.base_url, url)
        parsed = urlparse(url)
        if parsed.scheme not in ["http", "https"]:
            return None
            
        published_at_text = self._text(element, self.selectors.get("date"))
        
        return {
            "title": title,
            "url": url,
            "summary": self._text(element, self.selectors.get("description")),
            "source": self.source_key,
            "published_at": published_at_text,
        }

    def _parse_date(self, date_text: str) -> datetime:
        fallback_date = datetime.now(timezone.utc)
        if not date_text:
            logger.warning(f"Empty date text for article in {self.source_key}, using fallback: {fallback_date}")
            return fallback_date
            
        for date_format in self.date_formats:
            try:
                # Force UTC timezone for consistency if no tz is in format
                dt = datetime.strptime(date_text.strip(), date_format)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except (TypeError, ValueError):
                continue
                
        logger.warning(f"Failed to parse date '{date_text}' with formats {self.date_formats}. Using fallback: {fallback_date}")
        return fallback_date

    def crawl(self, max_articles: int = 10) -> List[Dict[str, Any]]:
        self.news_articles = []
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.driver = self.init_driver()
                
                if not self.navigate_to_page():
                    logger.error(f"Failed to navigate to {self.target_url}")
                    return []
                    
                elements = self.find_articles(self.selectors.get("article_container"))
                if not elements:
                    logger.warning(f"No articles found for {self.source_key} at {self.target_url}")
                    return []
                
                # Parse and filter duplicates
                seen_urls = set()
                seen_titles = set()
                
                for i, el in enumerate(elements):
                    if len(self.news_articles) >= max_articles:
                        break
                        
                    article = self._parse_article(el, i)
                    if not article:
                        continue
                        
                    if article["url"] in seen_urls or article["title"] in seen_titles:
                        continue
                        
                    seen_urls.add(article["url"])
                    seen_titles.add(article["title"])
                    
                    # Convert date text to datetime
                    if "published_at" in article and isinstance(article["published_at"], str):
                        article["published_at"] = self._parse_date(article["published_at"])
                        
                    self.news_articles.append(article)
                
                logger.info(f"Successfully crawled {len(self.news_articles)} articles from {self.source_key}")
                return self.news_articles
                
            except WebDriverException as e:
                logger.error(f"WebDriver exception during crawl (attempt {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise
            except Exception as e:
                logger.error(f"Unexpected error during crawl: {e}")
                raise
            finally:
                self.cleanup()
                
        return []
