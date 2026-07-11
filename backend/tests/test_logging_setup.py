import logging

from backend.utils.logging_setup import get_logger, setup_logging


def test_setup_logging_creates_file_handler_and_named_loggers(tmp_path):
    log_file = tmp_path / "nested" / "crawler.log"
    logger = setup_logging(str(log_file), log_level="DEBUG", console_output=False)
    logger.debug("hello")
    for handler in logger.handlers: handler.flush()
    assert log_file.exists()
    assert "hello" in log_file.read_text(encoding="utf-8")
    assert get_logger().name == "security_news_crawler"
    assert get_logger("worker").name.endswith(".worker")
    logger.handlers.clear()
