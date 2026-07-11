"""
Text processing utilities for CyberSec Assistant Platform.

Provides common text processing functions including sanitization,
formatting, and validation.
"""

import re
import html
from typing import Dict, Any, List


def sanitize_html(input_text: str) -> str:
    """Sanitize HTML input to prevent XSS attacks."""
    if not input_text:
        return ""

    # Escape HTML entities
    sanitized = html.escape(input_text)

    # Remove remaining HTML tags
    sanitized = re.sub(r'<[^>]+>', '', sanitized)

    return sanitized


def sanitize_input(input_text: str, max_length: int = 10000) -> str:
    """Sanitize user input for safe processing."""
    if not input_text:
        return ""

    # Trim whitespace
    sanitized = input_text.strip()

    # Limit length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    # Sanitize HTML
    sanitized = sanitize_html(sanitized)

    return sanitized


def truncate_text(text: str, max_length: int = 200, suffix: str = "...") -> str:
    """Truncate text to maximum length with suffix."""
    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def format_timestamp(timestamp, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format timestamp for display."""
    if timestamp is None:
        return ""

    try:
        return timestamp.strftime(format_str)
    except AttributeError:
        return str(timestamp)


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"

    size_kb = size_bytes / 1024
    if size_kb < 1024:
        return f"{size_kb:.2f} KB"

    size_mb = size_kb / 1024
    if size_mb < 1024:
        return f"{size_mb:.2f} MB"

    size_gb = size_mb / 1024
    return f"{size_gb:.2f} GB"


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"

    if seconds < 60:
        return f"{seconds:.1f}s"

    minutes = int(seconds / 60)
    remaining_seconds = seconds % 60

    if minutes < 60:
        return f"{minutes}m {remaining_seconds:.0f}s"

    hours = int(minutes / 60)
    remaining_minutes = minutes % 60

    return f"{hours}h {remaining_minutes}m"


def extract_urls(text: str) -> List[str]:
    """Extract URLs from text."""
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    return re.findall(url_pattern, text)


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_url(url: str) -> bool:
    """Validate URL format."""
    pattern = r'^http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    return re.match(pattern, url) is not None


def clean_whitespace(text: str) -> str:
    """Clean up whitespace in text."""
    # Replace multiple spaces with single space
    text = re.sub(r'\s+', ' ', text)

    # Remove leading/trailing whitespace
    text = text.strip()

    return text


def count_words(text: str) -> int:
    """Count words in text."""
    words = text.split()
    return len(words)


def count_sentences(text: str) -> int:
    """Count sentences in text."""
    # Simple sentence counting - split on period, question mark, exclamation
    sentences = re.split(r'[.!?]+', text)
    # Remove empty strings
    sentences = [s.strip() for s in sentences if s.strip()]
    return len(sentences)


def extract_keywords(text: str, min_length: int = 3, max_keywords: int = 10) -> List[str]:
    """Extract important keywords from text."""
    # Simple keyword extraction - common words removal
    common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'what', 'which', 'who', 'when', 'where', 'why', 'how'}

    # Clean and split text
    words = clean_whitespace(text).lower().split()

    # Filter words
    keywords = []
    for word in words:
        word = word.strip('.,!?;:"\'()[]{}')
        if len(word) >= min_length and word not in common_words and word.isalpha():
            keywords.append(word)

    # Count frequency
    word_freq: Dict[str, int] = {}
    for word in keywords:
        word_freq[word] = word_freq.get(word, 0) + 1

    # Sort by frequency and return top keywords
    sorted_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, freq in sorted_keywords[:max_keywords]]


def format_error_message(error: Exception, context: str = "") -> str:
    """Format error message for display."""
    message = f"Error: {str(error)}"
    if context:
        message = f"{context} - {message}"
    return message


def safe_string_cast(value: Any, default: str = "") -> str:
    """Safely cast value to string."""
    if value is None:
        return default

    try:
        return str(value)
    except Exception:
        return default


def normalize_whitespace(text: str) -> str:
    """Normalize all whitespace to single spaces."""
    return re.sub(r'\s+', ' ', text).strip()