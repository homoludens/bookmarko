"""
API error handlers and response formatting.
"""
from __future__ import annotations

from functools import wraps
from typing import Any, Callable

from flask import jsonify, request

from . import api_v1


def api_response(data: Any = None, message: str = None, status: int = 200) -> tuple:
    """
    Create a standardized API response.

    Args:
        data: Response data (dict or list)
        message: Optional message
        status: HTTP status code

    Returns:
        Tuple of (response, status_code)
    """
    response = {'success': 200 <= status < 300}

    if data is not None:
        response['data'] = data
    if message:
        response['message'] = message

    return jsonify(response), status


def error_response(message: str, status: int = 400, errors: dict = None) -> tuple:
    """
    Create a standardized error response.

    Args:
        message: Error message
        status: HTTP status code
        errors: Optional dict of field-specific errors

    Returns:
        Tuple of (response, status_code)
    """
    response = {
        'success': False,
        'error': message
    }

    if errors:
        response['errors'] = errors

    return jsonify(response), status


@api_v1.errorhandler(400)
def bad_request(error):
    """Handle 400 Bad Request errors."""
    return error_response('Bad request', 400)


@api_v1.errorhandler(401)
def unauthorized(error):
    """Handle 401 Unauthorized errors."""
    return error_response('Authentication required', 401)


@api_v1.errorhandler(403)
def forbidden(error):
    """Handle 403 Forbidden errors."""
    return error_response('Access forbidden', 403)


@api_v1.errorhandler(404)
def not_found(error):
    """Handle 404 Not Found errors."""
    return error_response('Resource not found', 404)


@api_v1.errorhandler(422)
def unprocessable_entity(error):
    """Handle 422 Unprocessable Entity errors."""
    return error_response('Validation error', 422)


@api_v1.errorhandler(500)
def internal_error(error):
    """Handle 500 Internal Server errors."""
    return error_response('Internal server error', 500)
