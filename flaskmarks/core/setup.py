"""
Legacy setup module for backward compatibility.

This module re-exports extension instances from the new extensions module.
New code should import directly from flaskmarks.core.extensions.
"""
from __future__ import annotations

from flask import current_app

from .extensions import db, migrate, login_manager as lm, bcrypt

# Re-export for backward compatibility
__all__ = ["db", "migrate", "lm", "bcrypt", "config", "app"]


def _get_app():
    """Get the current Flask application instance."""
    try:
        return current_app._get_current_object()
    except RuntimeError:
        # Outside of application context, import the default app
        from flaskmarks import app
        return app


def _get_config():
    """Get the current Flask application config."""
    return _get_app().config


class _ConfigProxy:
    """Proxy object for accessing Flask config."""

    def __getitem__(self, key):
        return _get_config()[key]

    def __contains__(self, key):
        return key in _get_config()

    def get(self, key, default=None):
        return _get_config().get(key, default)


config = _ConfigProxy()


class _AppProxy:
    """Proxy object for accessing Flask app."""

    def __getattr__(self, name):
        return getattr(_get_app(), name)

    def __call__(self, *args, **kwargs):
        return _get_app()(*args, **kwargs)


app = _AppProxy()
