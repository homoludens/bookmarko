"""
API authentication via tokens.

Provides token-based authentication for API access.
Tokens are generated using HMAC-SHA256 with the user's ID and a timestamp.
"""
from __future__ import annotations

import hashlib
import hmac
import time
from functools import wraps
from typing import Callable

from flask import request, g, current_app

from flaskmarks.core.extensions import db, bcrypt
from flaskmarks.models.user import User

from . import api_v1
from .errors import api_response, error_response


# Token validity period (24 hours in seconds)
TOKEN_VALIDITY = 86400


def generate_token(user: User) -> str:
    """
    Generate an API token for a user.

    Token format: {user_id}:{timestamp}:{signature}

    Args:
        user: User instance

    Returns:
        Token string
    """
    timestamp = int(time.time())
    secret = current_app.config['SECRET_KEY']
    message = f"{user.id}:{timestamp}"
    signature = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

    return f"{user.id}:{timestamp}:{signature}"


def verify_token(token: str) -> User | None:
    """
    Verify an API token and return the associated user.

    Args:
        token: Token string to verify

    Returns:
        User instance if valid, None otherwise
    """
    try:
        parts = token.split(':')
        if len(parts) != 3:
            return None

        user_id, timestamp, signature = parts
        user_id = int(user_id)
        timestamp = int(timestamp)

        # Check token expiration
        if time.time() - timestamp > TOKEN_VALIDITY:
            return None

        # Verify signature
        secret = current_app.config['SECRET_KEY']
        message = f"{user_id}:{timestamp}"
        expected_signature = hmac.new(
            secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_signature):
            return None

        return User.query.get(user_id)

    except (ValueError, TypeError):
        return None


def token_required(f: Callable) -> Callable:
    """
    Decorator to require valid API token for endpoint access.

    Token should be provided in Authorization header:
    Authorization: Bearer <token>
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')

        if not auth_header.startswith('Bearer '):
            return error_response('Missing or invalid Authorization header', 401)

        token = auth_header[7:]  # Remove 'Bearer ' prefix
        user = verify_token(token)

        if not user:
            return error_response('Invalid or expired token', 401)

        g.api_user = user
        return f(*args, **kwargs)

    return decorated


@api_v1.route('/auth/token', methods=['POST'])
def get_token():
    """
    Obtain an API token.

    Request body:
        {
            "username": "user@example.com",
            "password": "secret"
        }

    Response:
        {
            "success": true,
            "data": {
                "token": "1:1234567890:abc123...",
                "expires_in": 86400,
                "user": {
                    "id": 1,
                    "username": "user",
                    "email": "user@example.com"
                }
            }
        }
    """
    data = request.get_json()

    if not data:
        return error_response('Request body required', 400)

    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return error_response('Username and password required', 400)

    user = User.by_uname_or_email(username)

    if not user or not user.authenticate_user(password):
        return error_response('Invalid credentials', 401)

    token = generate_token(user)

    return api_response({
        'token': token,
        'expires_in': TOKEN_VALIDITY,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email
        }
    })


@api_v1.route('/auth/verify', methods=['GET'])
@token_required
def verify_token_endpoint():
    """
    Verify the current token is valid.

    Response:
        {
            "success": true,
            "data": {
                "user": {
                    "id": 1,
                    "username": "user",
                    "email": "user@example.com"
                }
            }
        }
    """
    user = g.api_user
    return api_response({
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email
        }
    })


@api_v1.route('/auth/refresh', methods=['POST'])
@token_required
def refresh_token():
    """
    Refresh the current token.

    Response:
        {
            "success": true,
            "data": {
                "token": "1:1234567890:abc123...",
                "expires_in": 86400
            }
        }
    """
    user = g.api_user
    token = generate_token(user)

    return api_response({
        'token': token,
        'expires_in': TOKEN_VALIDITY
    })
