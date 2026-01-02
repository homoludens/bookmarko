"""
Flaskmarks - A bookmark and feed management application.

This module provides the Flask application factory for creating
and configuring the Flaskmarks application.
"""
from __future__ import annotations

from flask import Flask


def create_app(config_object: str = "config") -> Flask:
    """
    Application factory for creating the Flask app.
    
    Args:
        config_object: The configuration object to load (default: 'config')
    
    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__)
    app.config.from_object(config_object)
    
    # Initialize extensions
    from flaskmarks.core.extensions import init_extensions
    init_extensions(app)
    
    # Register blueprints
    from flaskmarks.core.blueprints import register_blueprints
    register_blueprints(app)
    
    # Register error handlers
    from flaskmarks.core.error import register_error_handlers
    register_error_handlers(app)
    
    # Register template filters
    from flaskmarks.core.filters import register_filters
    register_filters(app)
    
    # Register CLI commands
    from flaskmarks.cli import register_cli
    register_cli(app)
    
    return app


# Create default app instance for backwards compatibility
# This allows imports like: from flaskmarks import app
app = create_app()
