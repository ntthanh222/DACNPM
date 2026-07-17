from backend.crawlers.config_driven import ConfigDrivenCrawler
from backend.crawlers.registry import registry


def test_registry_imports_and_creates_configured_crawlers():
    assert registry.list_crawlers()
    crawler = registry.get_crawler("thehackernews", headless=True)
    assert isinstance(crawler, ConfigDrivenCrawler)
    assert crawler.target_url.startswith("https://")
    assert crawler.selectors["article_container"]
