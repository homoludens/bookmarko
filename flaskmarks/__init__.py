"""
Flaskmarks - A bookmark and feed management application.

This module provides the Flask application factory for creating
and configuring the Flaskmarks application.
"""
from __future__ import annotations

import os

from flask import Flask

_PRODUCTION_ENV_NAMES = {'production', 'prod'}
_INSECURE_SECRET_KEY_VALUES = {'super-duper-secret-key-CHANGE-ME'}


def _is_production_runtime(app: Flask) -> bool:
    env_name = app.config.get('ENV') or os.environ.get('FLASK_ENV') or os.environ.get('ENV') or ''
    return str(env_name).strip().lower() in _PRODUCTION_ENV_NAMES


def _validate_required_production_config(app: Flask) -> None:
    missing = []
    if not os.environ.get('FLASK_SECRET_KEY'):
        missing.append('FLASK_SECRET_KEY')
    if not os.environ.get('DATABASE_URL'):
        missing.append('DATABASE_URL')
    if missing:
        raise RuntimeError(
            'Missing required production configuration: ' + ', '.join(missing)
        )

    secret_key = app.config.get('SECRET_KEY')
    if not secret_key or str(secret_key).strip() in _INSECURE_SECRET_KEY_VALUES:
        raise RuntimeError(
            'Invalid production configuration: FLASK_SECRET_KEY must be explicitly configured.'
        )

    if not app.config.get('SQLALCHEMY_DATABASE_URI'):
        raise RuntimeError(
            'Invalid production configuration: DATABASE_URL must be explicitly configured.'
        )


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
    if _is_production_runtime(app):
        _validate_required_production_config(app)
    
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
