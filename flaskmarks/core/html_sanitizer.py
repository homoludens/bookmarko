"""Sanitization helpers for externally sourced HTML content."""
from __future__ import annotations

from urllib.parse import urlparse

from bs4 import BeautifulSoup, Comment

# Conservative allowlist that keeps common readable/article formatting.
ALLOWED_TAGS = {
    "a",
    "abbr",
    "b",
    "blockquote",
    "br",
    "code",
    "dd",
    "del",
    "div",
    "dl",
    "dt",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "i",
    "img",
    "li",
    "ol",
    "p",
    "pre",
    "s",
    "small",
    "span",
    "strong",
    "sub",
    "sup",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "u",
    "ul",
}

ALLOWED_ATTRIBUTES = {
    "a": {"href", "title"},
    "abbr": {"title"},
    "img": {"src", "alt", "title"},
}

GLOBAL_ALLOWED_ATTRIBUTES = {"lang"}
URL_ATTRIBUTES = {"href", "src"}
ALLOWED_URL_SCHEMES = {"http", "https", "mailto"}
DROP_CONTENT_TAGS = {"script", "style", "iframe", "object", "embed", "svg", "math"}


def _is_allowed_url(value: str) -> bool:
    parsed = urlparse(value.strip())
    if not parsed.scheme:
        # Relative URLs are acceptable for rendered article content.
        return True
    return parsed.scheme.lower() in ALLOWED_URL_SCHEMES


def sanitize_external_html(content: str | None) -> str:
    """
    Sanitize untrusted external HTML with an allowlist policy.

    Returns an empty string for missing content.
    """
    if not content:
        return ""

    soup = BeautifulSoup(str(content), "html.parser")

    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    for tag in soup.find_all(True):
        tag_name = tag.name.lower()

        if tag_name not in ALLOWED_TAGS:
            if tag_name in DROP_CONTENT_TAGS:
                tag.decompose()
            else:
                tag.unwrap()
            continue

        allowed_for_tag = ALLOWED_ATTRIBUTES.get(tag_name, set()) | GLOBAL_ALLOWED_ATTRIBUTES
        cleaned_attributes: dict[str, str] = {}

        for attr_name, attr_value in tag.attrs.items():
            normalized_name = attr_name.lower()
            if normalized_name not in allowed_for_tag:
                continue

            if isinstance(attr_value, list):
                normalized_value = " ".join(str(item) for item in attr_value)
            else:
                normalized_value = str(attr_value)

            if normalized_name in URL_ATTRIBUTES and not _is_allowed_url(normalized_value):
                continue

            cleaned_attributes[normalized_name] = normalized_value

        tag.attrs = cleaned_attributes

    if soup.body:
        return "".join(str(node) for node in soup.body.contents)
    return str(soup)
