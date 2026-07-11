#!/usr/bin/env python3
"""
Security News Crawler Script
Crawls security news from multiple sources and saves to Supabase

Supported sources:
- The Hacker News (https://thehackernews.com)
- VnExpress Số hóa (https://vnexpress.net/so-hoa)
"""

import os
import sys
import argparse
import re
from datetime import datetime
from typing import List, Dict, Optional

# Add parent directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(parent_dir)

for path in [parent_dir, project_root]:
    if path not in sys.path:
        sys.path.insert(0, path)

from backend.crawlers.registry import registry
from backend.config.crawler_script_config import load_config
from backend.utils.logging_setup import setup_logging
from backend.utils.duplicate_detector import DuplicateDetector
from backend.utils.statistics import StatisticsTracker
from backend.utils.pid_manager import PIDManager

try:
    from backend.database.connection import supabase, supabase_admin
    from backend.database.models import SecurityNewsCreate
    # Force use of local PostgreSQL for development if available
    try:
        from backend.database.local_connection import get_local_admin_client, is_local_available
        if is_local_available():
            print("🔄 Using local PostgreSQL connection for crawler...")
            supabase_admin = get_local_admin_client()
            supabase = supabase_admin  # Use same client for both
    except ImportError:
        pass  # Use Supabase clients as normal
except ImportError as e:
    # For development/testing without database
    print(f"Warning: Could not import database modules: {e}")
    print("Running in test mode without database connection.")
    supabase = None
    supabase_admin = None
    SecurityNewsCreate = None


def is_relevant_security_news(article: Dict) -> tuple[bool, str]:
    """
    Check if an article is relevant to security news.

    This function implements multi-level filtering:
    1. Removes ads, promotional content, courses, webinars
    2. For general tech sources (VnExpress), requires security keywords
    3. For security-focused sources, uses more lenient filtering

    Args:
        article: Article dictionary with title, summary, source fields

    Returns:
        tuple[bool, str]: (is_relevant, reason) where reason explains why it was filtered
    """
    title = (article.get('title') or '').lower()
    summary = (article.get('summary') or '').lower()
    source = (article.get('source') or '').lower()
    content = f"{title} {summary}"

    # ===== AD/PROMOTIONAL CONTENT FILTERING =====
    # These patterns indicate content that should be filtered out from ALL sources
    ad_patterns = [
        # Educational/Course content
        r'\bearn a master(?:\'s)? degree?\b',
        r'\bbachelor\'s degree\b',
        r'\bonline course\b',
        r'\bcertification\b',
        r'\btraining course\b',
        r'\blearn\s+(?:cybersecurity|security|ethical hacking)\b',
        r'\bcourse\s+(?:for|in)\b',

        # Events/Webinars/Conferences
        r'\bwebinar\b',
        r'\bvirtual summit\b',
        r'\bconference\b',
        r'\b(?:register|sign up|join)\s+for\b',
        r'\b(?:save|register)\s+your\s+spot\b',
        r'\broundtable\b',
        r'\bpanel\s+discussion\b',
        r'\bfirefly\ chat\b',

        # Sponsored content
        r'\bsponsored\b',
        r'\bpaid\s+promotion\b',
        r'\badvertisement\b',
        r'\bpartner\s+content\b',
        r'\bpartner\s+with\s+us\b',

        # Hiring/Recruitment
        r'\b(?:we are )?hiring\b',
        r'\bjob\s+opening\b',
        r'\bcareer\s+opportunity\b',
        r'\bjoin\s+our\s+team\b',
        r'\b(?:now\s+)?accepting\b',
        r'\blooking\s+for\b',

        # Commercial/PR content
        r'\bannounces?\s+(?:new\s+)?(?:feature|product|service|launch|release)\b',
        r'\bunveils?\s+(?:new\s+)?',
        r'\blaunch(?:es)?\s+(?:new\s+)?(?:feature|product|service)\b',
        r'\bproduct\s+update\b',
        r'\bfeature\s+highlight\b',
    ]

    # Check for ad/promotional content
    for pattern in ad_patterns:
        if re.search(pattern, content):
            return False, f"Promotional/ad content: {pattern}"

    # ===== SECURITY RELEVANCE CHECKING =====

    # Security-related keywords (Vietnamese and English)
    security_keywords = [
        # Vietnamese keywords
        'lỗ hổng', 'lỗ hổng bảo mật', 'lỗ hổng zero-day',
        'mã độc', 'virus', 'trojan', 'ransomware', 'malware', 'spyware', 'botnet',
        'tấn công mạng', 'tin tặc', 'hacker', 'thủ phạm',
        'an ninh mạng', 'an ninh', 'bảo mật', 'cybersecurity',
        'rò rỉ', 'rò rỉ dữ liệu', 'lộ', 'biết', 'bị lộ',
        'phishing', 'lừa đảo', 'giả mạo', 'đánh cắp',
        'từ chối dịch vụ', 'ddos', 'tấn công ddos',
        'xâm nhập', 'khai thác', 'ràim', 'vadm',
        'cve', 'khẩu mã', 'mật khẩu', 'xác thực',
        'bột net', 'tường lửa', 'firewall',
        'nghiêm trọng', 'nguy hiểm', 'đe dọa', 'mối đe dọa',

        # English keywords
        'vulnerability', 'cve-', 'exploit', 'zero-day', '0day',
        'malware', 'ransomware', 'trojan', 'virus', 'backdoor', 'spyware', 'botnet', 'rootkit',
        'breach', 'leak', 'data breach', 'exposed', 'database leak',
        'phishing', 'social engineering', 'scam', 'fraud',
        'ddos', 'denial of service', 'distributed denial',
        'hacker', 'threat actor', 'apt', 'advanced persistent threat',
        'cybersecurity', 'cyber security', 'information security',
        'attack', 'compromise', 'hack', 'intrusion', 'infiltration',
        'patch', 'security update', 'security bulletin',
        'authentication', 'authorization', 'access control',
        'encryption', 'crypto', 'cryptography',
        'penetration testing', 'pen testing', 'pentest',
        'supply chain attack', 'zero-click',
        'critical severity', 'critical vulnerability',
        'remote code execution', 'rce',
        'sql injection', 'xss', 'csrf',
        'threat intelligence', 'indicator of compromise'
    ]

    # General technology sources that require STRICT security relevance
    strict_sources = ['vnexpress', 'vietnam', 'so-hoa']
    is_strict_source = any(strict_source in source for strict_source in strict_sources)

    if is_strict_source:
        # For VnExpress and similar sources, require at least ONE security keyword
        has_security_keyword = any(keyword in content for keyword in security_keywords)
        if not has_security_keyword:
            return False, "General tech content (no security keywords found)"

        # Additional filtering for common non-security topics in tech news
        non_security_tech_topics = [
            r'\bthị trường\s+nhà\s+ đất\b',
            r'\b(?:sự\s+)?kết\s+hôn\b',
            r'\bđiện\s+thoại\b',
            r'\bsmartphone\b',
            r'\blaptop\b',
            r'\bsamsung\b',
            r'\bapple\b',
            r'\biphone\b',
            r'\bandroid\b',
            r'\bgiá\s+(?:vàng|đô)\b',
            r'\b(?:tỷ\s+giá|exchange\s+rate)\b',
            r'\bxuất\s+nhập\s+khẩu\b',
            r'\bkinh\s+doanh\b',
            r'\bstartup\b',
            r'\bquỹ\s+đầu\s+tư\b',
        ]

        for topic in non_security_tech_topics:
            if re.search(topic, content):
                return False, f"Non-security tech topic: {topic}"

    # If we made it here, the article is relevant
    return True, "Relevant security content"


class SecurityNewsCrawlerApp:
    """Main application for crawling security news."""

    def __init__(
        self,
        config_path: Optional[str] = None,
        test_mode: bool = False,
        sources: Optional[List[str]] = None,
        use_pid_file: bool = False,
        fuzzy_detect: bool = False,
        similarity_threshold: float = 0.85,
        log_level: str = "INFO",
        max_articles: int = 10,
        headless: bool = False
    ):
        """
        Initialize the crawler application.

        Args:
            config_path: Path to configuration file
            test_mode: Run without database insertion
            sources: Specific sources to crawl
            use_pid_file: Use PID file to prevent concurrent runs
            fuzzy_detect: Enable fuzzy duplicate detection
            similarity_threshold: Similarity threshold for fuzzy matching
            log_level: Logging level
            max_articles: Maximum articles per source
            headless: Run in headless mode
        """
        # Load configuration
        self.config = load_config(config_path)

        # Override config with CLI arguments
        if headless:
            self.config.headless = True
        if log_level:
            self.config.log_level = log_level
        if fuzzy_detect:
            self.config.duplicate_detection_method = 'fuzzy'
            self.config.fuzzy_similarity_threshold = similarity_threshold
        if use_pid_file:
            self.config.use_pid_file = True

        # Setup logging
        self.logger = setup_logging(
            log_file=self.config.log_file,
            log_level=self.config.log_level,
            max_bytes=self.config.log_max_bytes,
            backup_count=self.config.log_backup_count
        )

        # Initialize components
        # Auto-enable test mode if database is unavailable
        if not test_mode:
            from backend.database.connection import supabase, supabase_admin
            if supabase is None and supabase_admin is None:
                logger.warning("⚠️ Database unavailable - automatically enabling test mode")
                test_mode = True

        self.test_mode = test_mode
        self.sources = sources
        self.max_articles = max_articles

        # Initialize duplicate detector
        self.duplicate_detector = DuplicateDetector(
            method=self.config.duplicate_detection_method,
            fuzzy_threshold=self.config.fuzzy_similarity_threshold
        )

        # Initialize statistics tracker
        self.statistics = StatisticsTracker(
            enabled=self.config.statistics_enabled,
            stats_file=self.config.statistics_file
        )

        # PID manager
        self.pid_manager = PIDManager(
            pid_file=self.config.pid_file,
            lock_timeout=self.config.lock_timeout
        ) if self.config.use_pid_file else None

    def run(self) -> bool:
        """
        Run the crawler application.

        Returns:
            True if successful, False otherwise
        """
        # Acquire PID lock if enabled
        if self.pid_manager:
            if not self.pid_manager.acquire_lock():
                self.logger.error("Another crawler instance is already running")
                return False

        try:
            # Start statistics tracking
            self.statistics.start()

            # Print banner
            self._print_banner()

            # Get enabled sources
            enabled_sources = {
                name: source_config.enabled
                for name, source_config in self.config.sources.items()
            }

            # Create crawlers
            crawlers = registry.create_crawlers(
                sources=self.sources,
                enabled_sources=enabled_sources,
                headless=self.config.headless,
                timeout=self.config.timeout,
                page_load_delay=self.config.page_load_delay
            )

            if not crawlers:
                self.logger.warning("No crawlers created, exiting")
                return True

            # Cache existing articles BEFORE crawling to reduce database queries
            self.logger.info("Caching existing articles for duplicate detection...")
            self.duplicate_detector.cache_existing_articles(limit=1000)

            # Crawl from each source
            all_articles = []
            for source_name, crawler in crawlers.items():
                try:
                    self.logger.info(f"Crawling from {source_name}...")

                    # Use context manager for WebDriver lifecycle
                    with crawler:
                        articles = crawler.crawl(max_articles=self.max_articles)

                    if articles:
                        all_articles.extend(articles)
                        self.statistics.record_article_found(source_name, len(articles))
                        self.statistics.record_article_parsed(source_name, len(articles))
                        self.logger.info(f"Successfully crawled {len(articles)} articles from {source_name}")
                    else:
                        self.logger.warning(f"No articles crawled from {source_name}")
                        self.statistics.record_error(source_name, 1)

                except Exception as e:
                    self.logger.error(f"Error crawling from {source_name}: {e}")
                    self.statistics.record_error(source_name, 1)

            if not all_articles:
                self.logger.warning("No articles were crawled from any source")
                return True

            # Save articles to database
            if self.test_mode:
                self._display_test_mode_summary(all_articles)
            else:
                self._save_articles_to_database(all_articles)

            # Stop statistics tracking and display summary
            self.statistics.stop()
            self.statistics.display_summary()

            # Save statistics to file
            if self.config.statistics_enabled:
                self.statistics.save_statistics()

            self.logger.info("Crawling completed successfully")
            return True

        except KeyboardInterrupt:
            self.logger.warning("Crawler interrupted by user")
            return False

        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return False

        finally:
            # Release PID lock if enabled
            if self.pid_manager:
                self.pid_manager.release_lock()

    def _print_banner(self):
        """Print the crawler banner."""
        print("=" * 60)
        print("🔒 Security News Crawler")
        print("=" * 60)
        print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🖥️  Headless mode: {self.config.headless}")
        print(f"🧪 Test mode: {self.test_mode}")
        print(f"📊 Duplicate detection: {self.config.duplicate_detection_method}")
        print(f"📰 Sources: {', '.join(self.sources) if self.sources else 'All enabled'}")
        print(f"📝 Max articles per source: {self.max_articles}")
        print("=" * 60 + "\n")

    def _save_articles_to_database(self, articles: List[Dict]):
        """
        Save articles to Supabase database with relevance filtering.

        Args:
            articles: List of article dictionaries
        """
        self.logger.info(f"Saving {len(articles)} articles to database...")

        inserted_count = 0
        skipped_count = 0
        relevance_filtered_count = 0

        for article in articles:
            try:
                # ===== RELEVANCE CHECK =====
                is_relevant, relevance_reason = is_relevant_security_news(article)

                if not is_relevant:
                    relevance_filtered_count += 1
                    source = article.get('source', 'Unknown')
                    self.statistics.record_article_skipped(source, 1)
                    self.logger.debug(f"Filtered non-relevant article: {article['title'][:50]}... ({relevance_reason})")
                    continue

                # ===== DUPLICATE CHECK =====
                duplicate_reason = self.duplicate_detector.is_duplicate(article)

                if duplicate_reason:
                    skipped_count += 1
                    source = article.get('source', 'Unknown')
                    self.statistics.record_article_skipped(source, 1)
                    self.logger.debug(f"Skipping duplicate: {article['title'][:50]}... ({duplicate_reason})")
                    continue

                # Convert datetime to ISO string for JSON serialization
                published_at = article['published_at']
                if hasattr(published_at, 'isoformat'):
                    published_at = published_at.isoformat()

                # Insert new article
                news_data = SecurityNewsCreate(
                    title=article['title'],
                    url=article['url'],
                    source=article['source'],
                    description=article.get('summary'),
                    published_at=published_at
                )

                if self.test_mode:
                    # In test mode, just log what would be inserted
                    self.logger.info(f"[TEST] Would insert: {article['title'][:50]}...")
                    inserted_count += 1
                else:
                    # Insert to database
                    db_client = supabase_admin if supabase_admin is not None else supabase
                    db_client.table('news_articles').insert(news_data.model_dump(mode='json')).execute()
                    inserted_count += 1
                    source = article.get('source', 'Unknown')
                    self.statistics.record_article_inserted(source, 1)
                    self.logger.info(f"Inserted: {article['title'][:50]}...")

            except Exception as e:
                self.logger.error(f"Error saving article: {e}")
                source = article.get('source', 'Unknown')
                self.statistics.record_error(source, 1)
                continue

        self.logger.info(f"\nDatabase update complete:")
        self.logger.info(f"   - Inserted: {inserted_count} new articles")
        self.logger.info(f"   - Skipped: {skipped_count} duplicates")
        self.logger.info(f"   - Filtered: {relevance_filtered_count} non-relevant articles")

    def _display_test_mode_summary(self, articles: List[Dict]):
        """
        Display a summary of articles that would be inserted in test mode.

        Args:
            articles: List of article dictionaries
        """
        print("\n" + "=" * 60)
        print("🧪 TEST MODE - Would insert the following articles:")
        print("=" * 60)

        relevant_count = 0
        irrelevant_count = 0
        duplicate_count = 0

        for idx, article in enumerate(articles, 1):
            print(f"\n{idx}. {article['title']}")
            print(f"   Source: {article['source']}")
            print(f"   URL: {article['url']}")
            print(f"   Date: {article['published_at']}")
            if article.get('summary'):
                print(f"   Summary: {article['summary'][:100]}...")

            # Check for relevance
            is_relevant, relevance_reason = is_relevant_security_news(article)
            if not is_relevant:
                irrelevant_count += 1
                print(f"   ❌ Would be filtered: {relevance_reason}")
            else:
                relevant_count += 1

            # Check for duplicates
            duplicate_reason = self.duplicate_detector.is_duplicate(article)
            if duplicate_reason:
                duplicate_count += 1
                print(f"   ⚠️ Would be skipped (duplicate): {duplicate_reason}")

        print("\n" + "=" * 60)
        print(f"Total articles processed: {len(articles)}")
        print(f"✅ Relevant articles: {relevant_count}")
        print(f"❌ Filtered (non-relevant): {irrelevant_count}")
        print(f"⚠️ Skipped (duplicates): {duplicate_count}")
        print(f"📊 Would be inserted: {relevant_count - duplicate_count}")
        print("=" * 60 + "\n")


def main():
    """Main entry point for the crawler application."""
    parser = argparse.ArgumentParser(
        description='Crawl security news from multiple sources and save to Supabase',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Run with default settings (both sources, 10 articles each)
  python scripts/crawl_security_news.py

  # Run with custom config file
  python scripts/crawl_security_news.py --config custom_config.yaml

  # Run specific sources
  python scripts/crawl_security_news.py --sources thehackernews vnexpress

  # Run only VnExpress
  python scripts/crawl_security_news.py --sources vnexpress

  # Run in test mode (no database insertion)
  python scripts/crawl_security_news.py --test-mode

  # Run with PID file management (for cron jobs)
  python scripts/crawl_security_news.py --use-pid-file --headless

  # Run with fuzzy duplicate detection
  python scripts/crawl_security_news.py --fuzzy-detect --similarity 0.9

  # Run with debug logging
  python scripts/crawl_security_news.py --log-level DEBUG

  # Run with 5 articles per source in headless mode
  python scripts/crawl_security_news.py --articles 5 --headless
        '''
    )

    # Configuration
    parser.add_argument(
        '--config', '-c',
        type=str,
        default=None,
        help='Path to configuration file (default: backend/scripts/config.yaml)'
    )

    # Source selection
    parser.add_argument(
        '--sources', '-s',
        type=str,
        nargs='+',
        choices=['thehackernews', 'vnexpress', 'securityweek', 'krebsonsecurity',
                 'bleepingcomputer', 'darkreading', 'helpnetsecurity', 'theregister'],
        default=None,
        help='Specific sources to crawl (default: all enabled sources)'
    )

    # Crawler settings
    parser.add_argument(
        '--articles', '-a',
        type=int,
        default=None,
        help='Maximum articles per source (default: from config)'
    )

    parser.add_argument(
        '--headless', '-H',
        action='store_true',
        help='Run browser in headless mode (for automated runs)'
    )

    # Testing
    parser.add_argument(
        '--test-mode', '-t',
        action='store_true',
        help='Run without database insertion (for testing)'
    )

    # Duplicate detection
    parser.add_argument(
        '--fuzzy-detect', '-f',
        action='store_true',
        help='Enable fuzzy duplicate detection'
    )

    parser.add_argument(
        '--similarity',
        type=float,
        default=0.85,
        help='Similarity threshold for fuzzy duplicate detection (default: 0.85)'
    )

    # Scheduled execution
    parser.add_argument(
        '--use-pid-file', '-p',
        action='store_true',
        help='Use PID file to prevent concurrent runs'
    )

    # Logging
    parser.add_argument(
        '--log-level', '-l',
        type=str,
        default=None,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Set log level (default: from config)'
    )

    args = parser.parse_args()

    # Create and run crawler application
    app = SecurityNewsCrawlerApp(
        config_path=args.config,
        test_mode=args.test_mode,
        sources=args.sources,
        use_pid_file=args.use_pid_file,
        fuzzy_detect=args.fuzzy_detect,
        similarity_threshold=args.similarity,
        log_level=args.log_level,
        max_articles=args.articles or 10,
        headless=args.headless
    )

    success = app.run()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
