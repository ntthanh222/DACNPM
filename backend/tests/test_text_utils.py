from datetime import datetime

from backend.utils import text_utils


def test_sanitize_html_escapes_markup_without_executing_it():
    assert text_utils.sanitize_html("<script>alert('x')</script>") == "&lt;script&gt;alert(&#x27;x&#x27;)&lt;/script&gt;"


def test_truncate_text_uses_default_and_custom_suffixes():
    assert text_utils.truncate_text("abcdefgh", max_length=6) == "abc..."
    assert text_utils.truncate_text("abcdefgh", max_length=6, suffix="~") == "abcde~"
    assert text_utils.truncate_text("short", max_length=6) == "short"


def test_format_timestamp_formats_datetimes_and_falls_back_to_strings():
    assert text_utils.format_timestamp(datetime(2026, 7, 10, 14, 30, 5)) == "2026-07-10 14:30:05"
    assert text_utils.format_timestamp("already formatted") == "already formatted"
    assert text_utils.format_timestamp(None) == ""


def test_format_file_size_converts_byte_units():
    assert text_utils.format_file_size(512) == "512 B"
    assert text_utils.format_file_size(1024) == "1.00 KB"
    assert text_utils.format_file_size(1024**2) == "1.00 MB"
    assert text_utils.format_file_size(1024**3) == "1.00 GB"


def test_format_duration_converts_milliseconds_through_hours():
    assert text_utils.format_duration(0.25) == "250ms"
    assert text_utils.format_duration(1.5) == "1.5s"
    assert text_utils.format_duration(125) == "2m 5s"
    assert text_utils.format_duration(3660) == "1h 1m"


def test_extract_urls_finds_multiple_http_urls():
    text = "Read https://example.com/docs and http://test.example/path?q=1."

    assert text_utils.extract_urls(text) == ["https://example.com/docs", "http://test.example/path?q=1."]


def test_count_words_and_sentences_handle_mixed_punctuation():
    text = "One sentence. Is this two? Yes!"

    assert text_utils.count_words(text) == 6
    assert text_utils.count_sentences(text) == 3


def test_extract_keywords_omits_stop_words_and_orders_by_frequency():
    text = "The scanner finds malware and malware in phishing reports."

    assert text_utils.extract_keywords(text) == ["malware", "scanner", "finds", "phishing", "reports"]


def test_safe_string_cast_and_normalize_whitespace_handle_edge_cases():
    assert text_utils.safe_string_cast(None, default="unknown") == "unknown"
    assert text_utils.safe_string_cast(42) == "42"
    assert text_utils.normalize_whitespace("  one\n\ttwo   three ") == "one two three"
