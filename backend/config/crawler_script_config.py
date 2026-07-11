"""Configuration management for security news crawler."""

import os
import yaml
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class RetryConfig:
    """Configuration for retry mechanism."""

    max_attempts: int = 3
    backoff_multiplier: float = 2.0
    initial_delay: float = 1.0


@dataclass
class SourceConfig:
    """Configuration for a specific news source."""

    enabled: bool = True
    max_articles: int = 10


@dataclass
class CrawlerConfig:
    """Main configuration for the security news crawler."""

    # Crawler settings
    headless: bool = False
    timeout: int = 10
    page_load_delay: int = 2
    max_articles_per_source: int = 10

    # Source configurations
    sources: Dict[str, SourceConfig] = field(default_factory=lambda: {
        'thehackernews': SourceConfig(enabled=True, max_articles=10),
        'vnexpress': SourceConfig(enabled=True, max_articles=10),
        'securityweek': SourceConfig(enabled=True, max_articles=10),
        'krebsonsecurity': SourceConfig(enabled=True, max_articles=10),
        'bleepingcomputer': SourceConfig(enabled=True, max_articles=10),
        'darkreading': SourceConfig(enabled=True, max_articles=10),
        'helpnetsecurity': SourceConfig(enabled=True, max_articles=10),
        'theregister': SourceConfig(enabled=True, max_articles=10),
    })

    # Duplicate detection
    duplicate_detection_method: str = 'url'  # url, fuzzy, both
    fuzzy_similarity_threshold: float = 0.85

    # Retry configuration
    retry: RetryConfig = field(default_factory=RetryConfig)

    # Logging configuration
    log_level: str = 'INFO'
    log_file: str = 'logs/crawler.log'
    log_max_bytes: int = 10 * 1024 * 1024  # 10MB
    log_backup_count: int = 5

    # Statistics configuration
    statistics_enabled: bool = True
    statistics_file: str = 'logs/statistics.json'

    # Scheduled execution
    use_pid_file: bool = False
    pid_file: str = '/tmp/crawler.pid'
    lock_timeout: int = 3600  # 1 hour

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'CrawlerConfig':
        """
        Create CrawlerConfig from dictionary.

        Args:
            config_dict: Dictionary with configuration

        Returns:
            CrawlerConfig instance
        """
        # Extract crawler settings
        crawler_config = config_dict.get('crawler', {})
        headless = crawler_config.get('headless', False)
        timeout = crawler_config.get('timeout', 10)
        page_load_delay = crawler_config.get('page_load_delay', 2)
        max_articles_per_source = crawler_config.get('max_articles_per_source', 10)

        # Extract source configurations
        sources_dict = config_dict.get('sources', {})
        sources = {}
        for source_name, source_data in sources_dict.items():
            sources[source_name] = SourceConfig(
                enabled=source_data.get('enabled', True),
                max_articles=source_data.get('max_articles', 10)
            )

        # Extract duplicate detection settings
        duplicate_config = config_dict.get('duplicate_detection', {})
        duplicate_method = duplicate_config.get('method', 'url')
        fuzzy_threshold = duplicate_config.get('fuzzy_similarity_threshold', 0.85)

        # Extract retry configuration
        retry_dict = config_dict.get('retry', {})
        retry_config = RetryConfig(
            max_attempts=retry_dict.get('max_attempts', 3),
            backoff_multiplier=retry_dict.get('backoff_multiplier', 2.0),
            initial_delay=retry_dict.get('initial_delay', 1.0)
        )

        # Extract logging configuration
        logging_config = config_dict.get('logging', {})
        log_level = logging_config.get('level', 'INFO')
        log_file = logging_config.get('file', 'logs/crawler.log')
        log_max_bytes = logging_config.get('max_bytes', 10 * 1024 * 1024)
        log_backup_count = logging_config.get('backup_count', 5)

        # Extract statistics configuration
        stats_config = config_dict.get('statistics', {})
        stats_enabled = stats_config.get('enabled', True)
        stats_file = stats_config.get('file', 'logs/statistics.json')

        # Extract scheduled execution configuration
        scheduled_config = config_dict.get('scheduled', {})
        use_pid_file = scheduled_config.get('use_pid_file', False)
        pid_file = scheduled_config.get('pid_file', '/tmp/crawler.pid')
        lock_timeout = scheduled_config.get('lock_timeout', 3600)

        return cls(
            headless=headless,
            timeout=timeout,
            page_load_delay=page_load_delay,
            max_articles_per_source=max_articles_per_source,
            sources=sources,
            duplicate_detection_method=duplicate_method,
            fuzzy_similarity_threshold=fuzzy_threshold,
            retry=retry_config,
            log_level=log_level,
            log_file=log_file,
            log_max_bytes=log_max_bytes,
            log_backup_count=log_backup_count,
            statistics_enabled=stats_enabled,
            statistics_file=stats_file,
            use_pid_file=use_pid_file,
            pid_file=pid_file,
            lock_timeout=lock_timeout
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert CrawlerConfig to dictionary.

        Returns:
            Dictionary representation of the configuration
        """
        return {
            'crawler': {
                'headless': self.headless,
                'timeout': self.timeout,
                'page_load_delay': self.page_load_delay,
                'max_articles_per_source': self.max_articles_per_source
            },
            'sources': {
                name: {
                    'enabled': source.enabled,
                    'max_articles': source.max_articles
                }
                for name, source in self.sources.items()
            },
            'duplicate_detection': {
                'method': self.duplicate_detection_method,
                'fuzzy_similarity_threshold': self.fuzzy_similarity_threshold
            },
            'retry': {
                'max_attempts': self.retry.max_attempts,
                'backoff_multiplier': self.retry.backoff_multiplier,
                'initial_delay': self.retry.initial_delay
            },
            'logging': {
                'level': self.log_level,
                'file': self.log_file,
                'max_bytes': self.log_max_bytes,
                'backup_count': self.log_backup_count
            },
            'statistics': {
                'enabled': self.statistics_enabled,
                'file': self.statistics_file
            },
            'scheduled': {
                'use_pid_file': self.use_pid_file,
                'pid_file': self.pid_file,
                'lock_timeout': self.lock_timeout
            }
        }


def load_config(config_path: Optional[str] = None) -> CrawlerConfig:
    """
    Load configuration from YAML file or use defaults.

    Args:
        config_path: Path to configuration file. If None, uses default config or defaults.

    Returns:
        CrawlerConfig instance
    """
    # Default configuration file paths
    default_paths = [
        'backend/scripts/config.yaml',
        'scripts/config.yaml',
        'config.yaml'
    ]

    # Try to load configuration file
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_dict = yaml.safe_load(f)
                return CrawlerConfig.from_dict(config_dict)
        except Exception as e:
            print(f"Warning: Could not load config from {config_path}: {e}")
            print("Using default configuration")

    # Try default paths
    for path in default_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    config_dict = yaml.safe_load(f)
                    return CrawlerConfig.from_dict(config_dict)
            except Exception as e:
                print(f"Warning: Could not load config from {path}: {e}")
                continue

    # Use default configuration
    return CrawlerConfig()


def save_config(config: CrawlerConfig, config_path: str) -> bool:
    """
    Save configuration to YAML file.

    Args:
        config: CrawlerConfig instance to save
        config_path: Path to save configuration file

    Returns:
        True if successful, False otherwise
    """
    try:
        config_dict = config.to_dict()
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)
        return True
    except Exception as e:
        print(f"Error saving config to {config_path}: {e}")
        return False
