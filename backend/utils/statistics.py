"""Statistics tracking for the security news crawler."""

import os
import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from collections import defaultdict

from utils.logging_setup import get_logger


class StatisticsTracker:
    """Track and report crawler statistics."""

    def __init__(self, enabled: bool = True, stats_file: str = 'logs/statistics.json'):
        """
        Initialize statistics tracker.

        Args:
            enabled: Whether statistics tracking is enabled
            stats_file: Path to statistics file for persistence
        """
        self.enabled = enabled
        self.stats_file = stats_file
        self.logger = get_logger('StatisticsTracker')

        # Statistics data
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

        # Per-source statistics
        self.source_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {
            'found': 0,
            'parsed': 0,
            'inserted': 0,
            'skipped': 0,
            'errors': 0
        })

        # Overall statistics
        self.total_found = 0
        self.total_parsed = 0
        self.total_inserted = 0
        self.total_skipped = 0
        self.total_errors = 0

        # Load existing statistics if file exists
        self._load_statistics()

    def start(self):
        """Start tracking statistics."""
        if not self.enabled:
            return

        self.start_time = time.time()
        self.logger.info("Statistics tracking started")

    def stop(self):
        """Stop tracking statistics."""
        if not self.enabled:
            return

        self.end_time = time.time()
        self.logger.info("Statistics tracking stopped")

    def record_article_found(self, source: str, count: int = 1):
        """
        Record that articles were found on a source.

        Args:
            source: News source name
            count: Number of articles found
        """
        if not self.enabled:
            return

        self.source_stats[source]['found'] += count
        self.total_found += count

    def record_article_parsed(self, source: str, count: int = 1):
        """
        Record that articles were successfully parsed from a source.

        Args:
            source: News source name
            count: Number of articles parsed
        """
        if not self.enabled:
            return

        self.source_stats[source]['parsed'] += count
        self.total_parsed += count

    def record_article_inserted(self, source: str, count: int = 1):
        """
        Record that articles were inserted into the database from a source.

        Args:
            source: News source name
            count: Number of articles inserted
        """
        if not self.enabled:
            return

        self.source_stats[source]['inserted'] += count
        self.total_inserted += count

    def record_article_skipped(self, source: str, count: int = 1):
        """
        Record that articles were skipped (duplicates) from a source.

        Args:
            source: News source name
            count: Number of articles skipped
        """
        if not self.enabled:
            return

        self.source_stats[source]['skipped'] += count
        self.total_skipped += count

    def record_error(self, source: str, count: int = 1):
        """
        Record that errors occurred on a source.

        Args:
            source: News source name
            count: Number of errors
        """
        if not self.enabled:
            return

        self.source_stats[source]['errors'] += count
        self.total_errors += count

    def get_duration(self) -> Optional[float]:
        """
        Get the duration of the crawling session.

        Returns:
            Duration in seconds, or None if not available
        """
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None

    def get_articles_per_minute(self) -> Optional[float]:
        """
        Get the rate of articles processed per minute.

        Returns:
            Articles per minute, or None if not available
        """
        duration = self.get_duration()
        if duration and duration > 0:
            return (self.total_parsed / duration) * 60
        return None

    def get_success_rate(self) -> Optional[float]:
        """
        Get the success rate of crawling.

        Returns:
            Success rate as percentage (0.0 to 100.0), or None if not available
        """
        if self.total_found > 0:
            return (self.total_parsed / self.total_found) * 100
        return None

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all statistics.

        Returns:
            Dictionary with all statistics
        """
        summary = {
            'timestamp': datetime.now().isoformat(),
            'duration_seconds': self.get_duration(),
            'articles_per_minute': self.get_articles_per_minute(),
            'success_rate': self.get_success_rate(),
            'total': {
                'found': self.total_found,
                'parsed': self.total_parsed,
                'inserted': self.total_inserted,
                'skipped': self.total_skipped,
                'errors': self.total_errors
            },
            'sources': dict(self.source_stats)
        }

        return summary

    def display_summary(self):
        """Display a formatted summary of statistics."""
        if not self.enabled:
            return

        print("\n" + "=" * 60)
        print("📊 CRAWLING STATISTICS")
        print("=" * 60)

        # Duration
        duration = self.get_duration()
        if duration:
            minutes, seconds = divmod(int(duration), 60)
            print(f"⏱️  Duration: {minutes}m {seconds}s")

        # Overall statistics
        print(f"\n📈 Overall:")
        print(f"   Found:     {self.total_found}")
        print(f"   Parsed:    {self.total_parsed}")
        print(f"   Inserted:  {self.total_inserted}")
        print(f"   Skipped:   {self.total_skipped}")
        print(f"   Errors:    {self.total_errors}")

        # Performance metrics
        articles_per_min = self.get_articles_per_minute()
        success_rate = self.get_success_rate()
        if articles_per_min:
            print(f"\n⚡ Performance:")
            print(f"   Rate:      {articles_per_min:.2f} articles/minute")
        if success_rate is not None:
            print(f"   Success:   {success_rate:.2f}%")

        # Per-source statistics
        if self.source_stats:
            print(f"\n📰 By Source:")
            for source, stats in self.source_stats.items():
                print(f"   {source}:")
                print(f"      Found:    {stats['found']}")
                print(f"      Parsed:   {stats['parsed']}")
                print(f"      Inserted: {stats['inserted']}")
                print(f"      Skipped:  {stats['skipped']}")
                print(f"      Errors:   {stats['errors']}")

        print("=" * 60 + "\n")

    def _load_statistics(self):
        """Load existing statistics from file."""
        if not self.enabled:
            return
        if not os.path.exists(self.stats_file):
            return

        try:
            with open(self.stats_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for source, stats in data.get('sources', {}).items():
                self.source_stats[source] = stats

            totals = data.get('total', {})
            self.total_found = totals.get('found', 0)
            self.total_parsed = totals.get('parsed', 0)
            self.total_inserted = totals.get('inserted', 0)
            self.total_skipped = totals.get('skipped', 0)
            self.total_errors = totals.get('errors', 0)
            self.logger.info(f"Loaded existing statistics from {self.stats_file}")

        except Exception as e:
            self.logger.warning(f"Could not load statistics file: {e}")

    def save_statistics(self) -> bool:
        """
        Save statistics to file.

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return True

        try:
            # Ensure directory exists
            stats_dir = os.path.dirname(self.stats_file)
            if stats_dir and not os.path.exists(stats_dir):
                os.makedirs(stats_dir)

            # Save statistics
            summary = self.get_summary()
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Saved statistics to {self.stats_file}")
            return True

        except Exception as e:
            self.logger.error(f"Error saving statistics: {e}")
            return False

    def reset(self):
        """Reset all statistics to zero."""
        if not self.enabled:
            return

        self.start_time = None
        self.end_time = None
        self.source_stats.clear()
        self.total_found = 0
        self.total_parsed = 0
        self.total_inserted = 0
        self.total_skipped = 0
        self.total_errors = 0

        self.logger.info("Statistics reset")
