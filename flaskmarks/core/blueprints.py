"""
Blueprint registration for the Flask application.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flask import Flask


def register_blueprints(app: Flask) -> None:
    """
    Register all application blueprints.

    Args:
        app: The Flask application instance
    """
    from flaskmarks.views.profile import profile
    from flaskmarks.views.auth import auth
    from flaskmarks.views.tags import tags
    from flaskmarks.views.marks import marks
    from flaskmarks.views.chat import chat
    from flaskmarks.api import api_v1

    app.register_blueprint(profile)
    app.register_blueprint(auth)
    app.register_blueprint(tags)
    app.register_blueprint(marks)
    app.register_blueprint(chat)
    app.register_blueprint(api_v1)
