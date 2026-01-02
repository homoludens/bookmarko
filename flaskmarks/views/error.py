"""
Error handler blueprint.

Note: Most error handlers are registered in flaskmarks/core/error.py.
This blueprint is kept for backward compatibility but is mostly unused.
"""
from __future__ import annotations

from flask import (
    Blueprint,
    flash,
    redirect,
    request,
    url_for,
)
from werkzeug.exceptions import HTTPException

from flaskmarks.core.error import is_safe_url

error = Blueprint('error', __name__)


@error.errorhandler(401)
def unauthorized(e: HTTPException) -> str:
    """Handle unauthorized access within this blueprint."""
    if (request.referrer
            and is_safe_url(request.referrer)
            and request.referrer != "/"):
        flash('Unauthorized access.', category='danger')
    return redirect(url_for('auth.login'))


@error.errorhandler(403)
def forbidden(e: HTTPException) -> str:
    """Handle forbidden access within this blueprint."""
    flash('Forbidden access.', category='danger')
    return redirect(url_for('marks.allmarks'))
