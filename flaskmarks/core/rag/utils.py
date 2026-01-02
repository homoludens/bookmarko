"""Utility functions for RAG processing."""
from __future__ import annotations

import re
from html import unescape


def strip_html_tags(html_content: str) -> str:
    """
    Remove HTML tags and clean up text content.

    Args:
        html_content: Raw HTML string

    Returns:
        Cleaned plain text
    """
    if not html_content:
        return ''

    # Remove script and style elements
    text = re.sub(
        r'<script[^>]*>.*?</script>',
        '',
        html_content,
        flags=re.DOTALL | re.IGNORECASE
    )
    text = re.sub(
        r'<style[^>]*>.*?</style>',
        '',
        text,
        flags=re.DOTALL | re.IGNORECASE
    )

    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)

    # Unescape HTML entities
    text = unescape(text)

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def truncate_text(text: str, max_length: int = 2000) -> str:
    """
    Truncate text to max_length, breaking at word boundary.

    Args:
        text: Text to truncate
        max_length: Maximum length

    Returns:
        Truncated text with ellipsis if needed
    """
    if not text or len(text) <= max_length:
        return text or ''

    truncated = text[:max_length]
    last_space = truncated.rfind(' ')
    if last_space > max_length * 0.8:
        truncated = truncated[:last_space]

    return truncated + '...'
