"""
Tag model for categorizing bookmarks.
"""
from __future__ import annotations

from ..core.setup import db


class Tag(db.Model):
    """Model representing a tag for categorizing marks."""

    __tablename__ = 'tags'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Unicode(255), nullable=False)

    def __init__(self, title: str) -> None:
        """
        Initialize a new Tag.

        Args:
            title: The tag title/name
        """
        self.title = title

    @classmethod
    def check(cls, title: str) -> Tag | None:
        """
        Check if a tag with the given title exists.

        Args:
            title: The tag title to search for

        Returns:
            Tag instance if found, None otherwise
        """
        return cls.query.filter(Tag.title == title).first()

    def __repr__(self) -> str:
        return f'<Tag {self.title!r}>'
