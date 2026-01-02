"""
JSON serializers for API models.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from flaskmarks.models.mark import Mark
from flaskmarks.models.tag import Tag
from flaskmarks.models.user import User


def serialize_datetime(dt: datetime | None) -> str | None:
    """Serialize datetime to ISO format string."""
    return dt.isoformat() if dt else None


def serialize_tag(tag: Tag) -> dict:
    """
    Serialize a Tag model to dict.

    Args:
        tag: Tag instance

    Returns:
        Dict with tag data
    """
    return {
        'id': tag.id,
        'title': tag.title
    }


def serialize_mark(mark: Mark, include_html: bool = False) -> dict:
    """
    Serialize a Mark model to dict.

    Args:
        mark: Mark instance
        include_html: Whether to include full_html content

    Returns:
        Dict with mark data
    """
    data = {
        'id': mark.id,
        'type': mark.type,
        'title': mark.title,
        'description': mark.description,
        'url': mark.url,
        'clicks': mark.clicks,
        'last_clicked': serialize_datetime(mark.last_clicked),
        'created': serialize_datetime(mark.created),
        'updated': serialize_datetime(mark.updated),
        'tags': [serialize_tag(tag) for tag in mark.tags]
    }

    if include_html:
        data['full_html'] = mark.full_html

    return data


def serialize_mark_list(marks: list[Mark]) -> list[dict]:
    """
    Serialize a list of Mark models.

    Args:
        marks: List of Mark instances

    Returns:
        List of dicts with mark data
    """
    return [serialize_mark(mark) for mark in marks]


def serialize_user(user: User, include_email: bool = True) -> dict:
    """
    Serialize a User model to dict.

    Args:
        user: User instance
        include_email: Whether to include email

    Returns:
        Dict with user data
    """
    data = {
        'id': user.id,
        'username': user.username,
        'per_page': user.per_page,
        'sort_type': user.sort_type,
        'last_logged': serialize_datetime(user.last_logged)
    }

    if include_email:
        data['email'] = user.email

    return data


def serialize_pagination(pagination) -> dict:
    """
    Serialize Flask-SQLAlchemy pagination info.

    Args:
        pagination: Pagination object

    Returns:
        Dict with pagination metadata
    """
    return {
        'page': pagination.page,
        'per_page': pagination.per_page,
        'total': pagination.total,
        'pages': pagination.pages,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev
    }
