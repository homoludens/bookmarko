"""
Mark CRUD and search API endpoints.
"""
from __future__ import annotations

from datetime import datetime as dt

from flask import request, g

from flaskmarks.core.extensions import db
from flaskmarks.models.mark import Mark
from flaskmarks.models.tag import Tag

from . import api_v1
from .auth import token_required
from .errors import api_response, error_response
from .serializers import serialize_mark, serialize_mark_list, serialize_pagination


@api_v1.route('/marks', methods=['GET'])
@token_required
def list_marks():
    """
    List all marks for the authenticated user.

    Query params:
        page (int): Page number (default 1)
        per_page (int): Items per page (default user's setting, max 100)
        type (str): Filter by type (bookmark, feed, youtube)
        sort (str): Sort by 'clicks', 'created', 'updated' (default: user's setting)

    Response:
        {
            "success": true,
            "data": {
                "marks": [...],
                "pagination": {...}
            }
        }
    """
    user = g.api_user

    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', user.per_page, type=int), 100)
    mark_type = request.args.get('type')
    sort = request.args.get('sort', user.sort_type)

    query = user.my_marks()

    # Filter by type
    if mark_type and mark_type in Mark.valid_types:
        query = query.filter(Mark.type == mark_type)

    # Apply sorting
    match sort:
        case 'clicks':
            query = query.order_by(Mark.clicks.desc(), Mark.created.desc())
        case 'created':
            query = query.order_by(Mark.created.desc())
        case 'updated':
            query = query.order_by(Mark.updated.desc())
        case _:
            query = query.order_by(Mark.clicks.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return api_response({
        'marks': serialize_mark_list(pagination.items),
        'pagination': serialize_pagination(pagination)
    })


@api_v1.route('/marks/<int:mark_id>', methods=['GET'])
@token_required
def get_mark(mark_id: int):
    """
    Get a specific mark by ID.

    Query params:
        include_html (bool): Include full_html content (default false)

    Response:
        {
            "success": true,
            "data": {...}
        }
    """
    user = g.api_user
    include_html = request.args.get('include_html', 'false').lower() == 'true'

    mark = user.get_mark_by_id(mark_id)

    if not mark:
        return error_response('Mark not found', 404)

    return api_response(serialize_mark(mark, include_html=include_html))


@api_v1.route('/marks', methods=['POST'])
@token_required
def create_mark():
    """
    Create a new mark.

    Request body:
        {
            "type": "bookmark",
            "title": "Example Site",
            "url": "https://example.com",
            "description": "Optional description",
            "tags": ["tag1", "tag2"]
        }

    Response:
        {
            "success": true,
            "data": {...},
            "message": "Mark created successfully"
        }
    """
    user = g.api_user
    data = request.get_json()

    if not data:
        return error_response('Request body required', 400)

    # Validate required fields
    errors = {}
    if not data.get('title'):
        errors['title'] = 'Title is required'
    if not data.get('url'):
        errors['url'] = 'URL is required'
    if not data.get('type'):
        errors['type'] = 'Type is required'
    elif data.get('type') not in Mark.valid_types:
        errors['type'] = f"Type must be one of: {', '.join(Mark.valid_types)}"

    if errors:
        return error_response('Validation failed', 422, errors)

    # Check for duplicate URL
    existing = user.q_marks_by_url(data['url'])
    if existing:
        return error_response('A mark with this URL already exists', 409)

    # Create the mark
    mark = Mark(owner_id=user.id)
    mark.type = data['type']
    mark.title = data['title']
    mark.url = data['url']
    mark.description = data.get('description')

    # Process tags
    tag_titles = data.get('tags', [])
    tags = []
    for title in tag_titles:
        title = title.lower().strip()
        if title:
            tag = Tag.check(title)
            if not tag:
                tag = Tag(title)
                db.session.add(tag)
            tags.append(tag)
    mark.tags = tags

    db.session.add(mark)
    db.session.commit()

    return api_response(
        serialize_mark(mark),
        message='Mark created successfully',
        status=201
    )


@api_v1.route('/marks/<int:mark_id>', methods=['PUT'])
@token_required
def update_mark(mark_id: int):
    """
    Update an existing mark.

    Request body:
        {
            "title": "Updated Title",
            "url": "https://example.com/updated",
            "description": "Updated description",
            "tags": ["tag1", "tag2"]
        }

    Response:
        {
            "success": true,
            "data": {...},
            "message": "Mark updated successfully"
        }
    """
    user = g.api_user
    data = request.get_json()

    if not data:
        return error_response('Request body required', 400)

    mark = user.get_mark_by_id(mark_id)

    if not mark:
        return error_response('Mark not found', 404)

    # Update fields if provided
    if 'title' in data:
        if not data['title']:
            return error_response('Title cannot be empty', 422, {'title': 'Title is required'})
        mark.title = data['title']

    if 'url' in data:
        if not data['url']:
            return error_response('URL cannot be empty', 422, {'url': 'URL is required'})
        # Check for duplicate URL (excluding current mark)
        existing = user.q_marks_by_url(data['url'])
        if existing and existing.id != mark.id:
            return error_response('A mark with this URL already exists', 409)
        mark.url = data['url']

    if 'description' in data:
        mark.description = data['description']

    if 'type' in data:
        if data['type'] not in Mark.valid_types:
            return error_response(
                f"Type must be one of: {', '.join(Mark.valid_types)}",
                422,
                {'type': 'Invalid type'}
            )
        mark.type = data['type']

    # Update tags if provided
    if 'tags' in data:
        tags = []
        for title in data['tags']:
            title = title.lower().strip()
            if title:
                tag = Tag.check(title)
                if not tag:
                    tag = Tag(title)
                    db.session.add(tag)
                tags.append(tag)
        mark.tags = tags

    mark.updated = dt.utcnow()
    db.session.commit()

    return api_response(serialize_mark(mark), message='Mark updated successfully')


@api_v1.route('/marks/<int:mark_id>', methods=['DELETE'])
@token_required
def delete_mark(mark_id: int):
    """
    Delete a mark.

    Response:
        {
            "success": true,
            "message": "Mark deleted successfully"
        }
    """
    user = g.api_user

    mark = user.get_mark_by_id(mark_id)

    if not mark:
        return error_response('Mark not found', 404)

    db.session.delete(mark)
    db.session.commit()

    return api_response(message='Mark deleted successfully')


@api_v1.route('/marks/<int:mark_id>/click', methods=['POST'])
@token_required
def increment_clicks(mark_id: int):
    """
    Increment click count for a mark.

    Response:
        {
            "success": true,
            "data": {"clicks": 5},
            "message": "Click recorded"
        }
    """
    user = g.api_user

    mark = user.get_mark_by_id(mark_id)

    if not mark:
        return error_response('Mark not found', 404)

    mark.clicks += 1
    mark.last_clicked = dt.utcnow()
    db.session.commit()

    return api_response({'clicks': mark.clicks}, message='Click recorded')


# Search endpoints

@api_v1.route('/marks/search', methods=['GET'])
@token_required
def search_marks():
    """
    Search marks by query string.

    Query params:
        q (str): Search query (required)
        page (int): Page number (default 1)
        per_page (int): Items per page (default user's setting, max 100)
        type (str): Filter by type (bookmark, feed, youtube)

    Response:
        {
            "success": true,
            "data": {
                "query": "search term",
                "marks": [...],
                "pagination": {...}
            }
        }
    """
    user = g.api_user

    query = request.args.get('q', '').strip()
    if not query:
        return error_response('Search query (q) is required', 400)

    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', user.per_page, type=int), 100)
    mark_type = request.args.get('type', '')

    pagination = user.q_marks_by_string(page, query, mark_type)

    return api_response({
        'query': query,
        'marks': serialize_mark_list(pagination.items),
        'pagination': serialize_pagination(pagination)
    })


@api_v1.route('/marks/by-tag/<tag_slug>', methods=['GET'])
@token_required
def get_marks_by_tag(tag_slug: str):
    """
    Get marks with a specific tag.

    Query params:
        page (int): Page number (default 1)
        per_page (int): Items per page (default user's setting, max 100)

    Response:
        {
            "success": true,
            "data": {
                "tag": "python",
                "marks": [...],
                "pagination": {...}
            }
        }
    """
    user = g.api_user

    page = request.args.get('page', 1, type=int)

    pagination = user.q_marks_by_tag(tag_slug, page)

    return api_response({
        'tag': tag_slug,
        'marks': serialize_mark_list(pagination.items),
        'pagination': serialize_pagination(pagination)
    })


@api_v1.route('/marks/export', methods=['GET'])
@token_required
def export_marks():
    """
    Export all marks as JSON.

    Response:
        {
            "success": true,
            "data": {
                "marks": [...],
                "total": 150,
                "exported_at": "2024-01-15T10:30:00"
            }
        }
    """
    user = g.api_user

    marks = user.all_marks()

    return api_response({
        'marks': serialize_mark_list(marks),
        'total': len(marks),
        'exported_at': dt.utcnow().isoformat()
    })


@api_v1.route('/marks/stats', methods=['GET'])
@token_required
def get_stats():
    """
    Get mark statistics for the user.

    Response:
        {
            "success": true,
            "data": {
                "total": 150,
                "by_type": {
                    "bookmark": 120,
                    "feed": 25,
                    "youtube": 5
                }
            }
        }
    """
    user = g.api_user

    stats = {
        'total': user.my_marks().count(),
        'by_type': {
            mark_type: user.get_mark_type_count(mark_type)
            for mark_type in Mark.valid_types
        }
    }

    return api_response(stats)
