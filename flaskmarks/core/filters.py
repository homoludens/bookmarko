"""
Jinja2 template filters for the Flask application.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from webhelpers2.date import time_ago_in_words

if TYPE_CHECKING:
    from flask import Flask


def register_filters(app: Flask) -> None:
    """
    Register all Jinja2 template filters.

    Args:
        app: The Flask application instance
    """

    @app.template_filter('date')
    def filter_date(dateobj: datetime) -> str:
        """Format a datetime as YYYY-MM-DD."""
        return dateobj.strftime('%Y-%m-%d')

    @app.template_filter('length')
    def filter_length(items: list) -> int:
        """Return the length of a list."""
        return len(items)

    @app.template_filter('tagsize')
    def filter_tagsize(items: list) -> str:
        """Calculate CSS font size based on list length."""
        size = len(items)
        if size <= 1:
            size = 2
        return f"style=font-size:{size * 5}px"

    @app.template_filter('datetime')
    def filter_datetime(dateobj: datetime) -> str:
        """Format a datetime as YYYY-MM-DD HH:MM:SS."""
        return dateobj.strftime('%Y-%m-%d %H:%M:%S')

    @app.template_filter('datetimestr')
    def filter_datetimestr(datetimestr: str) -> str:
        """Parse and format an ISO datetime string."""
        date_n_time = datetimestr.split('T')
        time_parts = date_n_time[1].split('.')
        return f"{date_n_time[0]} {time_parts[0]}"

    @app.template_filter('sectomin')
    def filter_sectomin(sec: float | int) -> str:
        """Convert seconds to minutes."""
        return f"{float(sec) / 60:.2f}"

    @app.template_filter('thousandsep')
    def filter_thousandsep(arg: Any) -> str:
        """Format a number with thousand separators."""
        return f'{int(arg):,}'

    @app.template_filter('datewordsstr')
    def filter_datewordsstr(datetimestr: str) -> str:
        """Convert ISO datetime string to relative words."""
        date_n_time = datetimestr.split('T')
        time_parts = date_n_time[1].split('.')
        date_str = f"{date_n_time[0]} {time_parts[0]}"
        dateobj = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        return time_ago_in_words(dateobj, round=True, granularity='day')

    @app.template_filter('datewords')
    def filter_datewords(dateobj: datetime) -> str:
        """Convert datetime to relative words."""
        return time_ago_in_words(dateobj, round=True, granularity='day')

    @app.template_filter('enumerate')
    def filter_enumerate(items: list) -> enumerate:
        """Enumerate a list."""
        return enumerate(items)
