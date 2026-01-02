"""
Core module for Flaskmarks application.

This module contains extensions, blueprints, error handlers, and filters.
"""
from __future__ import annotations

from .extensions import db, migrate, login_manager, bcrypt, bootstrap

__all__ = ["db", "migrate", "login_manager", "bcrypt", "bootstrap"]
