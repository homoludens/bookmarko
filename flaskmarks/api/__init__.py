"""
REST API package for Flaskmarks.

Provides versioned API endpoints for programmatic access to bookmarks.
"""
from __future__ import annotations

from flask import Blueprint

# Create API v1 blueprint
api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')

# Import routes after blueprint creation to avoid circular imports
from . import auth, marks, tags, errors, quickadd
