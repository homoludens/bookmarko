"""
Background thread for importing bookmarks from URLs.
"""
from __future__ import annotations

from threading import Thread
from typing import Any
from urllib.parse import urlparse

import requests
import tldextract
from flask import current_app
from newspaper import Article, ArticleBinaryDataException
from readability.readability import Document

from flaskmarks.core.extensions import db
from flaskmarks.core.html_sanitizer import sanitize_external_html
from flaskmarks.core.youtube import get_youtube_info, check_url_video
from flaskmarks.models import Mark
from flaskmarks.models.tag import Tag


def fetch_url_metadata(url: str) -> dict[str, Any] | None:
    """
    Fetch metadata from a URL without saving to database.

    Args:
        url: The URL to fetch metadata from

    Returns:
        Dictionary with extracted metadata or None if failed
    """
    url_domain = tldextract.extract(url).domain
    readable_title = None

    m: dict[str, Any] = {
        'type': 'bookmark',
        'tags': [],
        'url': url,
        'title': url,
        'description': '',
        'full_html': '',
    }

    # Handle YouTube URLs
    if url_domain in ['youtube', 'youtu'] and check_url_video(url):
        print(f"Processing YouTube URL: {url_domain}")
        try:
            youtube_info = get_youtube_info(url)
            m['title'] = youtube_info['title']
            m['description'] = youtube_info['description']
            m['full_html'] = (
                youtube_info['description'] + youtube_info['subtitles']
            )

            m['tags'].append(url_domain)
            m['tags'].append('video')

            if youtube_info['uploader']:
                m['tags'].append(youtube_info['uploader'])

            for auto_tag in youtube_info['tags']:
                m['tags'].append(auto_tag)

            m['full_html'] = sanitize_external_html(m['full_html'])
            return m
        except Exception as e:
            print(f"YouTube extraction failed: {e}")
            m['full_html'] = sanitize_external_html(m['full_html'])
            return m

    # Check content type
    try:
        with requests.head(url, timeout=4) as r:
            content_type = r.headers.get('content-type', 'none')

            if 'text' not in content_type:
                m['tags'].append('binary_file')
                print(f'URL {url} is not text content')
                return m
    except Exception as e:
        print(f'Connection error for {url}: {e}')
        return None

    # Parse article content
    article = Article(url)

    try:
        article.download()
    except ArticleBinaryDataException:
        print(f"URL {url} is binary data")
        return m

    try:
        article.parse()
        article.nlp()
    except Exception as e:
        print(f"Article {url} parsing failed: {e}")
    else:
        if article.is_parsed:
            full_html = article.html

            if full_html:
                readable = Document(full_html)
                readable_html = readable.summary()
                readable_title = readable.title()
                m['full_html'] = sanitize_external_html(readable_html)
                m['description'] = article.summary
            else:
                m['full_html'] = sanitize_external_html(article.summary)
                m['description'] = article.summary
        else:
            m['full_html'] = sanitize_external_html(url)

        m['title'] = readable_title if readable_title else url

        # Add tags and keywords
        m['tags'].append(url_domain)

        for auto_tag in article.keywords[:5]:
            m['tags'].append(auto_tag)

    m['full_html'] = sanitize_external_html(m['full_html'])
    print(f'Metadata fetched for: "{m["title"]}"')
    return m


class MarksImportThread(Thread):
    """
    Thread class for importing a bookmark from a URL.

    Fetches content, extracts metadata, and saves to database.
    """

    def __init__(self, url: str, user_id: int) -> None:
        """
        Initialize the import thread.

        Args:
            url: The URL to import
            user_id: The ID of the user to associate the mark with
        """
        super().__init__()
        self.url = url
        self.user_id = user_id
        self.m: dict[str, Any] | None = None

    def run(self) -> dict[str, Any] | None:
        """
        Execute the import process.

        Returns:
            Dictionary with mark data or None if import failed
        """
        if self.is_url_valid(self.url, self.user_id):
            self.get_url_data()
        return self.m

    def uri_validator(self, url_to_test: str) -> bool:
        """
        Validate URL format.

        Args:
            url_to_test: URL string to validate

        Returns:
            True if valid URL, False otherwise
        """
        try:
            result = urlparse(url_to_test)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    def is_url_valid(self, url: str, user_id: int) -> bool:
        """
        Check if URL is valid and not already imported.

        Args:
            url: The URL to check
            user_id: The user ID to check against

        Returns:
            True if URL is valid and not a duplicate
        """
        # Import app here to avoid circular imports
        from flaskmarks import app

        with app.app_context():
            # Test if it looks like a URL
            if not self.uri_validator(url):
                print("not valid uri")
                return False

            existing_mark = Mark.query.filter(
                Mark.url == url,
                Mark.owner_id == user_id
            ).all()

            if existing_mark:
                current_app.logger.debug(
                    f'Mark with this url "{url}" already exists.'
                )
                print("exists!")
                return False

            return True

    def get_url_data(self) -> None:
        """Fetch and extract data from the URL."""
        url = self.url
        url_domain = tldextract.extract(url).domain
        readable_title = None

        m: dict[str, Any] = {
            'type': 'bookmark',
            'tags': [],
            'url': url,
            'title': url,
            'description': '',
            'full_html': '',
        }

        # Handle YouTube URLs
        if url_domain in ['youtube', 'youtu'] and check_url_video(url):
            print(url_domain)
            youtube_info = get_youtube_info(url)
            m['title'] = youtube_info['title']
            m['description'] = youtube_info['description']
            m['full_html'] = (
                youtube_info['description'] + youtube_info['subtitles']
            )

            m['tags'].append(url_domain)
            m['tags'].append('video')

            # Some videos don't have channel
            if youtube_info['uploader']:
                m['tags'].append(youtube_info['uploader'])

            for auto_tag in youtube_info['tags']:
                m['tags'].append(auto_tag)

            m['full_html'] = sanitize_external_html(m['full_html'])
            self.m = m
            return

        # Check content type
        try:
            with requests.head(url, timeout=4) as r:
                content_type = r.headers.get('content-type', 'none')

                if 'text' not in content_type:
                    m['tags'].append('binary_file')
                    print('url not text')
                    self.m = m
                    return
        except Exception as e:
            print('requests connection error')
            print(e)
            return

        # Parse article content
        article = Article(url)

        try:
            article.download()
        except ArticleBinaryDataException:
            print(f"URL {url} is binary data")

        try:
            article.parse()
            article.nlp()
        except Exception:
            print(f"Article {url} not working: article not able to be parsed")
        else:
            if article.is_parsed:
                full_html = article.html

                if full_html:
                    readable = Document(full_html)
                    readable_html = readable.summary()
                    readable_title = readable.title()
                    m['full_html'] = sanitize_external_html(readable_html)
                    m['description'] = article.summary
                else:
                    m['full_html'] = sanitize_external_html(article.summary)
                    m['description'] = article.summary
            else:
                m['full_html'] = sanitize_external_html(url)

            m['title'] = readable_title if readable_title else url

            # Add tags and keywords
            m['tags'].append(url_domain)

            for auto_tag in article.keywords[:5]:
                m['tags'].append(auto_tag)

        print(f'New bookmark: "{m["title"]}", added.')

        m['full_html'] = sanitize_external_html(m['full_html'])
        self.m = m
        self.insert_mark_thread()

    def insert_mark_thread(self) -> None:
        """Insert the mark into the database."""
        data = self.m
        if not data:
            return

        # Import app here to avoid circular imports
        from flaskmarks import app

        with app.app_context():
            m = Mark(self.user_id)
            m.url = data['url']
            m.title = data['title']
            m.description = data['description']
            m.full_html = sanitize_external_html(data['full_html'])
            m.type = data['type']

            for auto_tag in data['tags']:
                m.tags.append(Tag(auto_tag))

            try:
                db.session.add(m)
                db.session.commit()
            except Exception as e:
                print(e)
                db.session.rollback()
