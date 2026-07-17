import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from pathlib import Path
from backend.crawlers.config_driven import ConfigDrivenCrawler

@pytest.fixture
def mock_config():
    return {
        "test_source": {
            "source_name": "Test Source",
            "base_url": "https://example.com",
            "target_url": "https://example.com/news",
            "selectors": {
                "article_container": ".article",
                "title": "h2",
                "description": "p",
                "date": ".date"
            },
            "date_formats": ["%Y-%m-%d"]
        }
    }

@patch("backend.crawlers.config_driven.yaml.safe_load")
@patch("backend.crawlers.config_driven.Path.exists", return_value=True)
@patch("backend.crawlers.config_driven.Path.open")
def test_valid_config(mock_open, mock_exists, mock_yaml, mock_config):
    mock_yaml.return_value = mock_config
    crawler = ConfigDrivenCrawler("test_source")
    assert crawler.base_url == "https://example.com"
    assert crawler.selectors["title"] == "h2"

@patch("backend.crawlers.config_driven.yaml.safe_load")
@patch("backend.crawlers.config_driven.Path.exists", return_value=True)
@patch("backend.crawlers.config_driven.Path.open")
def test_invalid_config_missing_title(mock_open, mock_exists, mock_yaml, mock_config):
    del mock_config["test_source"]["selectors"]["title"]
    mock_yaml.return_value = mock_config
    with pytest.raises(ValueError, match="title selector is required"):
        ConfigDrivenCrawler("test_source")

@patch("backend.crawlers.config_driven.yaml.safe_load")
@patch("backend.crawlers.config_driven.Path.exists", return_value=True)
@patch("backend.crawlers.config_driven.Path.open")
def test_parse_date_valid(mock_open, mock_exists, mock_yaml, mock_config):
    mock_yaml.return_value = mock_config
    crawler = ConfigDrivenCrawler("test_source")
    dt = crawler._parse_date("2023-10-01")
    assert dt == datetime(2023, 10, 1, tzinfo=timezone.utc)

@patch("backend.crawlers.config_driven.yaml.safe_load")
@patch("backend.crawlers.config_driven.Path.exists", return_value=True)
@patch("backend.crawlers.config_driven.Path.open")
def test_parse_date_invalid_fallback(mock_open, mock_exists, mock_yaml, mock_config):
    mock_yaml.return_value = mock_config
    crawler = ConfigDrivenCrawler("test_source")
    dt = crawler._parse_date("invalid date")
    assert dt.tzinfo == timezone.utc
    assert dt.year == datetime.now(timezone.utc).year

@patch("backend.crawlers.config_driven.yaml.safe_load")
@patch("backend.crawlers.config_driven.Path.exists", return_value=True)
@patch("backend.crawlers.config_driven.Path.open")
def test_parse_article_relative_url(mock_open, mock_exists, mock_yaml, mock_config):
    mock_yaml.return_value = mock_config
    crawler = ConfigDrivenCrawler("test_source")
    
    mock_element = MagicMock()
    mock_title_node = MagicMock()
    mock_title_node.text = "Test Title"
    mock_title_node.get_attribute.return_value = "/article/1"
    
    def find_element_side_effect(by, selector):
        if selector == "h2":
            return mock_title_node
        elif selector == "p":
            desc = MagicMock()
            desc.text = "Summary"
            return desc
        elif selector == ".date":
            date = MagicMock()
            date.text = "2023-10-01"
            return date
        raise Exception("Not found")
        
    mock_element.find_element.side_effect = find_element_side_effect
    
    article = crawler._parse_article(mock_element, 0)
    assert article is not None
    assert article["title"] == "Test Title"
    assert article["url"] == "https://example.com/article/1"
    
@patch("backend.crawlers.config_driven.yaml.safe_load")
@patch("backend.crawlers.config_driven.Path.exists", return_value=True)
@patch("backend.crawlers.config_driven.Path.open")
def test_parse_article_malformed_url(mock_open, mock_exists, mock_yaml, mock_config):
    mock_yaml.return_value = mock_config
    crawler = ConfigDrivenCrawler("test_source")
    
    mock_element = MagicMock()
    mock_title_node = MagicMock()
    mock_title_node.text = "Test Title"
    mock_title_node.get_attribute.return_value = "javascript:alert(1)"
    
    def find_element_side_effect(by, selector):
        if selector == "h2":
            return mock_title_node
        raise Exception("Not found")
        
    mock_element.find_element.side_effect = find_element_side_effect
    
    article = crawler._parse_article(mock_element, 0)
    assert article is None
