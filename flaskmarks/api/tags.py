"""
Tag management API endpoints.
"""
from __future__ import annotations

from flask import request, g

from flaskmarks.core.extensions import db
from flaskmarks.models.tag import Tag
from flaskmarks.models.mark import Mark

from . import api_v1
from .auth import token_required
from .errors import api_response, error_response
from .serializers import serialize_tag, serialize_pagination


@api_v1.route('/tags', methods=['GET'])
@token_required
def list_tags():
    """
    List all tags used by the authenticated user.

    Query params:
        page (int): Page number (default 1)
        per_page (int): Items per page (default 50, max 100)
        sort (str): Sort by 'title' or 'count' (default 'title')

    Response:
        {
            "success": true,
            "data": {
                "tags": [
                    {"id": 1, "title": "python", "count": 15},
                    ...
                ],
                "pagination": {...}
            }
        }
    """
    user = g.api_user

    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 50, type=int), 100)
    sort = request.args.get('sort', 'title')

    # Get tags with mark count for this user
    query = user.my_tags()

    if sort == 'title':
        query = query.order_by(Tag.title)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # Serialize tags with count
    tags_data = []
    for tag in pagination.items:
        tag_dict = serialize_tag(tag)
        # Count marks with this tag for this user
        tag_dict['count'] = (
            user.my_marks()
            .filter(Mark.tags.any(id=tag.id))
            .count()
        )
        tags_data.append(tag_dict)

    # Sort by count if requested (post-query sort since count is computed)
    if sort == 'count':
        tags_data.sort(key=lambda x: x['count'], reverse=True)

    return api_response({
        'tags': tags_data,
        'pagination': serialize_pagination(pagination)
    })


@api_v1.route('/tags/<int:tag_id>', methods=['GET'])
@token_required
def get_tag(tag_id: int):
    """
    Get a specific tag by ID.

    Response:
        {
            "success": true,
            "data": {
                "id": 1,
                "title": "python",
                "count": 15
            }
        }
    """
    user = g.api_user

    tag = Tag.query.get(tag_id)

    if not tag:
        return error_response('Tag not found', 404)

    # Check if user has marks with this tag
    count = user.my_marks().filter(Mark.tags.any(id=tag.id)).count()

    if count == 0:
        return error_response('Tag not found', 404)

    tag_dict = serialize_tag(tag)
    tag_dict['count'] = count

    return api_response(tag_dict)


@api_v1.route('/tags', methods=['POST'])
@token_required
def create_tag():
    """
    Create a new tag.

    Note: Tags are typically created when creating/updating marks.
    This endpoint is for pre-creating tags.

    Request body:
        {
            "title": "newtag"
        }

    Response:
        {
            "success": true,
            "data": {"id": 1, "title": "newtag"},
            "message": "Tag created successfully"
        }
    """
    data = request.get_json()

    if not data:
        return error_response('Request body required', 400)

    title = data.get('title', '').lower().strip()

    if not title:
        return error_response('Tag title is required', 422, {'title': 'Title is required'})

    # Check if tag already exists
    existing = Tag.check(title)
    if existing:
        return error_response('Tag already exists', 409)

    tag = Tag(title)
    db.session.add(tag)
    db.session.commit()

    return api_response(
        serialize_tag(tag),
        message='Tag created successfully',
        status=201
    )


@api_v1.route('/tags/<int:tag_id>', methods=['PUT'])
@token_required
def update_tag(tag_id: int):
    """
    Rename a tag.

    Request body:
        {
            "title": "newname"
        }

    Response:
        {
            "success": true,
            "data": {"id": 1, "title": "newname"},
            "message": "Tag updated successfully"
        }
    """
    user = g.api_user
    data = request.get_json()

    if not data:
        return error_response('Request body required', 400)

    tag = Tag.query.get(tag_id)

    if not tag:
        return error_response('Tag not found', 404)

    # Check if user has marks with this tag
    count = user.my_marks().filter(Mark.tags.any(id=tag.id)).count()

    if count == 0:
        return error_response('Tag not found', 404)

    title = data.get('title', '').lower().strip()

    if not title:
        return error_response('Tag title is required', 422, {'title': 'Title is required'})

    # Check for duplicate
    existing = Tag.check(title)
    if existing and existing.id != tag.id:
        return error_response('A tag with this name already exists', 409)

    tag.title = title
    db.session.commit()

    tag_dict = serialize_tag(tag)
    tag_dict['count'] = count

    return api_response(tag_dict, message='Tag updated successfully')


@api_v1.route('/tags/<int:tag_id>', methods=['DELETE'])
@token_required
def delete_tag(tag_id: int):
    """
    Remove a tag from all user's marks.

    Note: This doesn't delete the tag from the database, just removes
    it from all marks owned by the authenticated user.

    Response:
        {
            "success": true,
            "message": "Tag removed from 15 marks"
        }
    """
    user = g.api_user

    tag = Tag.query.get(tag_id)

    if not tag:
        return error_response('Tag not found', 404)

    # Get all user's marks with this tag
    marks = user.my_marks().filter(Mark.tags.any(id=tag.id)).all()

    if not marks:
        return error_response('Tag not found', 404)

    # Remove tag from all marks
    count = len(marks)
    for mark in marks:
        mark.tags = [t for t in mark.tags if t.id != tag.id]

    db.session.commit()

    return api_response(message=f'Tag removed from {count} marks')


@api_v1.route('/tags/cloud', methods=['GET'])
@token_required
def get_tag_cloud():
    """
    Get tag cloud data (tags with their usage counts).

    Response:
        {
            "success": true,
            "data": {
                "tags": [
                    {"id": 1, "title": "python", "count": 25},
                    {"id": 2, "title": "flask", "count": 15},
                    ...
                ],
                "total": 50
            }
        }
    """
    user = g.api_user

    all_tags = user.all_tags()

    tags_data = []
    for tag in all_tags:
        count = user.my_marks().filter(Mark.tags.any(id=tag.id)).count()
        if count > 0:
            tags_data.append({
                'id': tag.id,
                'title': tag.title,
                'count': count
            })

    # Sort by count descending
    tags_data.sort(key=lambda x: x['count'], reverse=True)

    return api_response({
        'tags': tags_data,
        'total': len(tags_data)
    })
