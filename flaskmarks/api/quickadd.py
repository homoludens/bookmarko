"""
Quick-add API endpoint for browser extensions.

Provides a fast endpoint for saving bookmarks from browser extensions
with async metadata extraction.
"""
from __future__ import annotations

import threading
from datetime import datetime as dt
from urllib.parse import urlparse

from flask import request, g, current_app

from flaskmarks.core.extensions import db
from flaskmarks.core.html_sanitizer import sanitize_external_html
from flaskmarks.core.marks_import_thread import fetch_url_metadata
from flaskmarks.models.mark import Mark
from flaskmarks.models.tag import Tag

from . import api_v1
from .auth import token_required
from .errors import api_response, error_response
from .serializers import serialize_mark


def is_valid_url(url: str) -> bool:
    """Validate URL format."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def async_metadata_extraction(mark_id: int, url: str, app) -> None:
    """
    Background task to extract metadata and update the mark.

    Args:
        mark_id: ID of the mark to update
        url: URL to extract metadata from
        app: Flask application instance
    """
    with app.app_context():
        try:
            # Fetch metadata without inserting
            data = fetch_url_metadata(url)

            if data:
                mark = Mark.query.get(mark_id)
                if mark:
                    # Update title if it was just the URL
                    if mark.title == url and data.get('title') and data['title'] != url:
                        mark.title = data['title']

                    # Update description if empty
                    if not mark.description and data.get('description'):
                        mark.description = data['description']

                    # Update full_html if empty
                    if not mark.full_html and data.get('full_html'):
                        mark.full_html = sanitize_external_html(data['full_html'])

                    # Add auto-extracted tags
                    if data.get('tags'):
                        existing_tag_titles = {t.title.lower() for t in mark.tags}
                        for tag_title in data['tags']:
                            tag_title = str(tag_title).lower().strip()
                            if tag_title and tag_title not in existing_tag_titles:
                                tag = Tag.check(tag_title)
                                if not tag:
                                    tag = Tag(tag_title)
                                    db.session.add(tag)
                                mark.tags.append(tag)

                    mark.updated = dt.utcnow()
                    db.session.commit()
                    current_app.logger.info(f"Metadata extracted for mark {mark_id}: {mark.title}")

        except Exception as e:
            current_app.logger.error(f"Error extracting metadata for mark {mark_id}: {e}")
            import traceback
            traceback.print_exc()


@api_v1.route('/quickadd', methods=['POST'])
@token_required
def quickadd():
    """
    Quick-add a bookmark from browser extension.

    Creates bookmark immediately with provided data, then triggers
    async metadata extraction to enrich the bookmark.

    Request body (JSON):
        {
            "url": "https://example.com/article",  (required)
            "title": "Article Title",               (optional, defaults to URL)
            "description": "Description",           (optional)
            "tags": ["tag1", "tag2"]               (optional)
        }

    Alternative formats supported:
        - Form data with 'url', 'title', 'tags' fields
        - Query parameters: ?url=...&title=...&tags=tag1,tag2

    Response:
        {
            "success": true,
            "data": {
                "id": 123,
                "url": "https://example.com/article",
                "title": "Article Title",
                "status": "created",
                "metadata_extraction": "pending"
            },
            "message": "Bookmark saved"
        }
    """
    user = g.api_user

    # Support multiple input formats for extension compatibility
    if request.is_json:
        data = request.get_json()
    elif request.form:
        # Form data support for bookmarklet
        data = {
            'url': request.form.get('url', ''),
            'title': request.form.get('title', ''),
            'description': request.form.get('description', ''),
            'tags': request.form.get('tags', '').split(',') if request.form.get('tags') else []
        }
    else:
        # Query parameter support for simple bookmarklet
        data = {
            'url': request.args.get('url', ''),
            'title': request.args.get('title', ''),
            'description': request.args.get('description', ''),
            'tags': request.args.get('tags', '').split(',') if request.args.get('tags') else []
        }

    if not data:
        return error_response('Request data required', 400)

    url = data.get('url', '').strip()

    if not url:
        return error_response('URL is required', 400, {'url': 'URL is required'})

    if not is_valid_url(url):
        return error_response('Invalid URL format', 400, {'url': 'Must be a valid URL with scheme (http/https)'})

    # Check for duplicate
    existing = user.q_marks_by_url(url)
    if existing:
        return api_response(
            {
                'id': existing.id,
                'url': existing.url,
                'title': existing.title,
                'status': 'exists',
                'metadata_extraction': 'not_needed'
            },
            message='Bookmark already exists',
            status=200
        )

    # Create the mark immediately with provided data
    mark = Mark(owner_id=user.id)
    mark.type = 'bookmark'
    mark.url = url
    mark.title = data.get('title', '').strip() or url
    mark.description = data.get('description', '').strip() or None

    # Add mark to session first to avoid autoflush warnings
    db.session.add(mark)

    # Process tags
    tag_input = data.get('tags', [])
    if isinstance(tag_input, str):
        tag_input = [t.strip() for t in tag_input.split(',') if t.strip()]

    for title in tag_input:
        title = title.lower().strip()
        if title:
            tag = Tag.check(title)
            if not tag:
                tag = Tag(title)
                db.session.add(tag)
            mark.tags.append(tag)

    db.session.commit()

    mark_id = mark.id

    # Always trigger async metadata extraction to get full_html, description, and tags
    # even if title was provided by the extension
    extraction_status = 'pending'
    app = current_app._get_current_object()
    thread = threading.Thread(
        target=async_metadata_extraction,
        args=(mark_id, url, app)
    )
    thread.daemon = True
    thread.start()

    return api_response(
        {
            'id': mark_id,
            'url': mark.url,
            'title': mark.title,
            'tags': [t.title for t in mark.tags],
            'status': 'created',
            'metadata_extraction': extraction_status
        },
        message='Bookmark saved',
        status=201
    )


@api_v1.route('/quickadd', methods=['GET'])
@token_required
def quickadd_get():
    """
    Quick-add via GET request (for simple bookmarklet support).

    Query parameters:
        url: The URL to bookmark (required)
        title: Optional title
        tags: Comma-separated tags

    Example bookmarklet:
        javascript:(function(){
            window.open('https://your-server/api/v1/quickadd?url='+encodeURIComponent(location.href)+'&title='+encodeURIComponent(document.title)+'&token=YOUR_TOKEN');
        })();
    """
    # Reuse the POST logic
    return quickadd()


@api_v1.route('/quickadd/status/<int:mark_id>', methods=['GET'])
@token_required
def quickadd_status(mark_id: int):
    """
    Check the status of a quick-added bookmark.

    Useful for extensions to poll and get updated metadata.

    Response:
        {
            "success": true,
            "data": {
                "id": 123,
                "title": "Fetched Article Title",
                "description": "Auto-extracted description",
                "tags": ["auto", "extracted", "tags"],
                "has_content": true,
                "updated": "2024-01-15T10:30:00"
            }
        }
    """
    user = g.api_user

    mark = user.get_mark_by_id(mark_id)

    if not mark:
        return error_response('Mark not found', 404)

    return api_response({
        'id': mark.id,
        'url': mark.url,
        'title': mark.title,
        'description': mark.description,
        'tags': [t.title for t in mark.tags],
        'has_content': bool(mark.full_html),
        'created': mark.created.isoformat() if mark.created else None,
        'updated': mark.updated.isoformat() if mark.updated else None
    })


@api_v1.route('/bookmarklet/script', methods=['GET'])
def get_bookmarklet_script():
    """
    Generate a bookmarklet script for quick saving.

    Query parameters:
        token: API token to embed (required)
        server: Server URL override (optional)

    Response:
        {
            "success": true,
            "data": {
                "bookmarklet": "javascript:...",
                "instructions": "Drag this to your bookmarks bar..."
            }
        }

    Note: This endpoint does not require authentication so users
    can generate the bookmarklet with their token embedded.
    """
    token = request.args.get('token')

    if not token:
        return error_response('Token parameter required', 400)

    # Get server URL from request or parameter
    server = request.args.get('server') or request.host_url.rstrip('/')

    # Generate bookmarklet code
    bookmarklet = f"""javascript:(function(){{
var url=encodeURIComponent(location.href);
var title=encodeURIComponent(document.title);
var xhr=new XMLHttpRequest();
xhr.open('POST','{server}/api/v1/quickadd',true);
xhr.setRequestHeader('Content-Type','application/json');
xhr.setRequestHeader('Authorization','Bearer {token}');
xhr.onload=function(){{
    var r=JSON.parse(xhr.responseText);
    if(r.success){{alert('Saved: '+r.data.title);}}
    else{{alert('Error: '+r.error);}}
}};
xhr.onerror=function(){{alert('Network error');}};
xhr.send(JSON.stringify({{url:decodeURIComponent(url),title:decodeURIComponent(title)}}));
}})();"""

    # Minified version (remove newlines and extra spaces)
    bookmarklet_min = bookmarklet.replace('\n', '').replace('    ', '')

    return api_response({
        'bookmarklet': bookmarklet_min,
        'bookmarklet_readable': bookmarklet,
        'instructions': (
            '1. Copy the bookmarklet code\n'
            '2. Create a new bookmark in your browser\n'
            '3. Paste the code as the URL/location\n'
            '4. Click the bookmark on any page to save it'
        )
    })
