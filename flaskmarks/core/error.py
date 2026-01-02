"""
Error handlers and authentication utilities.
"""
from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlparse, urljoin

from flask import flash, redirect, url_for, g, request
from flask_login import current_user

from .extensions import login_manager, db

if TYPE_CHECKING:
    from flask import Flask


@login_manager.user_loader
def load_user(user_id: str):
    """
    Load a user by ID for Flask-Login.
    
    Args:
        user_id: The user ID as a string
    
    Returns:
        User instance or None
    """
    from flaskmarks.models import User
    return db.session.get(User, int(user_id))


def register_error_handlers(app: Flask) -> None:
    """
    Register error handlers and before_request hooks.
    
    Args:
        app: The Flask application instance
    """
    
    @app.before_request
    def before_request():
        """Set current user in flask.g for template access."""
        g.user = current_user
    
    @app.errorhandler(401)
    def unauthorized(error):
        """Handle unauthorized access."""
        if (request.referrer 
            and is_safe_url(request.referrer) 
            and request.referrer != "/"):
            flash('Unauthorized access.', category='danger')
        return redirect(url_for('auth.login'))
    
    @app.errorhandler(403)
    def forbidden(error):
        """Handle forbidden access."""
        flash('Forbidden access.', category='danger')
        return redirect(url_for('marks.allmarks'))
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle not found errors."""
        flash('Page not found.', category='warning')
        return redirect(url_for('marks.allmarks'))


def is_safe_url(target: str) -> bool:
    """
    Check if a URL is safe for redirection.
    
    Args:
        target: The URL to check
    
    Returns:
        True if the URL is safe, False otherwise
    """
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return (
        test_url.scheme in ('http', 'https') 
        and ref_url.netloc == test_url.netloc
    )
