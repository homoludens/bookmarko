"""
Flask extensions initialization.

This module provides centralized extension instances and initialization.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_bootstrap import Bootstrap
from flask_migrate import Migrate

if TYPE_CHECKING:
    from flask import Flask

# Extension instances
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
bcrypt = Bcrypt()
bootstrap = Bootstrap()


def init_extensions(app: Flask) -> None:
    """
    Initialize all Flask extensions with the application.

    Args:
        app: The Flask application instance
    """
    # Database
    db.init_app(app)
    migrate.init_app(app, db)

    # Authentication
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"

    # Security
    bcrypt.init_app(app)

    # UI
    bootstrap.init_app(app)

    # Debug toolbar (only in debug mode)
    if app.debug:
        try:
            from flask_debugtoolbar import DebugToolbarExtension
            DebugToolbarExtension(app)
        except ImportError:
            pass
