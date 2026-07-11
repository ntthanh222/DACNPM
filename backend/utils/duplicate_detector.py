"""Duplicate detection for news articles."""

import sys
import os
# Add parent directory to path for database imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Optional, List
from difflib import SequenceMatcher
import re

try:
    from database.connection import supabase
except ImportError:
    try:
        from backend.database.connection import supabase
    except ImportError:
        # For standalone usage, we'll handle this at runtime
        supabase = None

from utils.logging_setup import get_logger


class DuplicateDetector:
    """Detect duplicate news articles by URL and fuzzy title matching."""

    def __init__(
        self,
        method: str = 'url',
        fuzzy_threshold: float = 0.85
    ):
        """
        Initialize duplicate detector.

        Args:
            method: Detection method ('url', 'fuzzy', or 'both')
            fuzzy_threshold: Similarity threshold for fuzzy matching (0.0 to 1.0)
        """
        self.method = method.lower()
        self.fuzzy_threshold = fuzzy_threshold
        self.logger = get_logger('DuplicateDetector')

        # Cache for existing articles to reduce database queries
        self._existing_urls = None
        self._existing_titles = None

    def is_duplicate(self, article: dict) -> Optional[str]:
        """
        Check if an article is a duplicate.

        Args:
            article: Article dictionary with 'title', 'url', 'source'

        Returns:
            Reason string if duplicate, None otherwise
        """
        url = article.get('url')
        title = article.get('title')

        if not url or not title:
            self.logger.warning("Article missing URL or title")
            return None

        # Check by URL
        if self.method in ['url', 'both']:
            if self._is_duplicate_by_url(url):
                return "URL already exists"

        # Check by fuzzy title matching
        if self.method in ['fuzzy', 'both']:
            duplicate = self._is_duplicate_by_title(title, article.get('source'))
            if duplicate:
                return f"Similar title found: {duplicate}"

        return None

    def _is_duplicate_by_url(self, url: str) -> bool:
        """
        Check if article URL already exists.

        Args:
            url: Article URL to check

        Returns:
            True if duplicate, False otherwise
        """
        try:
            # Use cache if available
            if self._existing_urls is not None:
                return url in self._existing_urls

            # Query database
            if supabase is None:
                self.logger.debug("Database unavailable - skipping URL duplicate check")
                return False
            result = supabase.table('news_articles')\
                .select('url')\
                .eq('url', url)\
                .execute()

            return len(result.data) > 0

        except Exception as e:
            self.logger.error(f"Error checking URL duplicate: {e}")
            return False

    def _is_duplicate_by_title(self, title: str, source: Optional[str] = None) -> Optional[str]:
        """
        Check if article title is similar to existing articles.

        Args:
            title: Article title to check
            source: Article source (optional, for filtering)

        Returns:
            Similar title if found, None otherwise
        """
        try:
            # ✅ FIX: Use cache if available
            if self._existing_titles is not None:
                return self._find_similar_title(title, self._existing_titles, "cached")

            # Fallback: Query database if cache not available
            if supabase is None:
                self.logger.debug("Database unavailable - skipping title duplicate check")
                return None
            query = supabase.table('news_articles')\
                .select('title', 'source')\
                .order('created_at', desc=True)\
                .limit(100)

            if source:
                query = query.eq('source', source)

            result = query.execute()

            if not result.data:
                return None

            titles = (article.get('title', '') for article in result.data)
            return self._find_similar_title(title, titles, "db query")

        except Exception as e:
            self.logger.error(f"Error checking title duplicate: {e}")
            return None

    def _find_similar_title(self, title: str, titles, source_label: str) -> Optional[str]:
        for existing_title in titles:
            similarity = self._calculate_similarity(title, existing_title)
            if similarity < self.fuzzy_threshold:
                continue

            self.logger.debug(
                f"Found similar title ({source_label}): {similarity:.2f} "
                f"'{title[:50]}...' vs '{existing_title[:50]}...'"
            )
            return existing_title
        return None

    @staticmethod
    def _calculate_similarity(text1: str, text2: str) -> float:
        """
        Calculate similarity between two text strings.

        Args:
            text1: First text string
            text2: Second text string

        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Normalize text: lowercase, remove extra spaces, remove special characters
        text1 = DuplicateDetector._normalize_text(text1)
        text2 = DuplicateDetector._normalize_text(text2)

        # Calculate similarity
        return SequenceMatcher(None, text1, text2).ratio()

    @staticmethod
    def _normalize_text(text: str) -> str:
        """
        Normalize text for comparison.

        Args:
            text: Text to normalize

        Returns:
            Normalized text
        """
        # Convert to lowercase
        text = text.lower()

        # Remove special characters and extra spaces
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text)

        return text.strip()

    def cache_existing_articles(self, limit: int = 1000):
        """
        Cache existing articles from database to reduce queries.

        Args:
            limit: Maximum number of articles to cache
        """
        try:
            # Cache URLs
            url_result = supabase.table('news_articles')\
                .select('url')\
                .limit(limit)\
                .execute()

            self._existing_urls = set(
                article['url'] for article in url_result.data
            )

            # Cache titles (for fuzzy matching)
            title_result = supabase.table('news_articles')\
                .select('title')\
                .limit(limit)\
                .execute()

            self._existing_titles = [
                article['title'] for article in title_result.data
            ]

            self.logger.info(f"Cached {len(self._existing_urls)} URLs and "
                           f"{len(self._existing_titles)} titles")

        except Exception as e:
            self.logger.error(f"Error caching existing articles: {e}")

    def clear_cache(self):
        """Clear cached articles."""
        self._existing_urls = None
        self._existing_titles = None
        self.logger.debug("Cleared duplicate detector cache")

    def get_duplicate_count(self, articles: List[dict]) -> int:
        """
        Count duplicates in a list of articles.

        Args:
            articles: List of article dictionaries

        Returns:
            Number of duplicate articles
        """
        duplicate_count = 0

        for article in articles:
            if self.is_duplicate(article):
                duplicate_count += 1

        return duplicate_count
