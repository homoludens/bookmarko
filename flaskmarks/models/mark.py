"""
Mark model for storing bookmarks, feeds, and YouTube links.
"""
from __future__ import annotations

from datetime import datetime as dt
from typing import Any

from sqlalchemy import event, Column, Text, Computed
from sqlalchemy.sql import func
# from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import TSVECTOR
from pgvector.sqlalchemy import Vector
# from sqlalchemy_fulltext import FullText


from ..core.setup import db
from .tag import Tag


ass_tbl = db.Table(
    'marks_tags',
    db.metadata,
    db.Column('left_id', db.Integer, db.ForeignKey('marks.id')),
    db.Column('right_id', db.Integer, db.ForeignKey('tags.id'))
)


class Mark(db.Model):
    """
    Model representing a bookmark, feed, or YouTube link.

    Supports fulltext search on title, description, full_html, and url.
    """
    __tablename__ = 'marks'
    # __fulltext_columns__ = ('title', 'description', 'full_html', 'url')

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    type = db.Column(db.Unicode(255), nullable=False)
    title = db.Column(db.Unicode(255), nullable=False)
    description = db.Column(Text(), nullable=True)
    full_html = db.Column(Text(), nullable=True)
    url = db.Column(db.Unicode(512), nullable=False)
    clicks = db.Column(db.Integer, default=0)
    last_clicked = db.Column(db.DateTime)
    created = db.Column(db.DateTime)
    updated = db.Column(db.DateTime)
    # PostgreSQL generated column - computed automatically from title and full_html
    search_vector = db.Column(
        TSVECTOR,
        Computed(
            "setweight(to_tsvector('english', COALESCE(title, '')), 'A') || "
            "setweight(to_tsvector('english', COALESCE(full_html, '')), 'B')",
            persisted=True
        )
    )

    # RAG embedding columns
    embedding = db.Column(Vector(384), nullable=True)
    embedding_updated = db.Column(db.DateTime, nullable=True)

    tags = relationship(
        'Tag',
        secondary=ass_tbl,
        lazy='joined',
        backref='marks'
    )

    # Create a GiST or GIN index for better performance
    __table_args__ = (
        db.Index('idx_search_vector', 'search_vector', postgresql_using='gin'),
    )

    valid_types = ['bookmark', 'feed', 'youtube']
    valid_feed_types = ['feed', 'youtube']

    def __init__(self, owner_id: int, created: dt | None = None) -> None:
        """
        Initialize a new Mark.

        Args:
            owner_id: ID of the user who owns this mark
            created: Optional creation timestamp (defaults to now)
        """
        self.owner_id = owner_id
        self.created = created if created else dt.utcnow()

    def insert_from_import(self, data: dict[str, Any]) -> None:
        """
        Populate mark from imported data.

        Args:
            data: Dictionary containing mark data from import
        """
        self.title = data['title']
        self.type = data['type']

        # Catch wrongfully placed YouTube feeds
        if 'gdata.youtube.com' in data['url']:
            self.type = 'youtube'

        self.url = data['url']
        self.clicks = data['clicks']
        self.created = dt.fromtimestamp(int(data['created']))

        if data['updated']:
            self.updated = dt.fromtimestamp(int(data['updated']))
        if data['last_clicked']:
            self.last_clicked = dt.fromtimestamp(int(data['last_clicked']))

        # Process tags
        tags = []
        for t in data['tags']:
            tag = Tag.check(t.lower())
            if not tag:
                tag = Tag(t.lower())
                db.session.add(tag)
            tags.append(tag)
        self.tags = tags

    def __repr__(self) -> str:
        return f'<Mark {self.title!r}>'

    def get_embedding_text(self) -> str:
        """
        Generate the text to be embedded for this mark.
        Combines title, description, tags, and cleaned HTML content.

        Returns:
            Combined text for embedding generation
        """
        from flaskmarks.core.rag.utils import strip_html_tags

        tags_str = ', '.join(
            tag.title for tag in self.tags
        ) if self.tags else ''
        content = strip_html_tags(self.full_html) if self.full_html else ''

        # Truncate content to reasonable length (first ~2000 chars)
        if len(content) > 2000:
            content = content[:2000] + '...'

        return f"""Title: {self.title}
Description: {self.description or 'No description'}
Tags: {tags_str or 'No tags'}
Content: {content}
URL: {self.url}"""

    def needs_embedding_update(self) -> bool:
        """
        Check if embedding needs to be regenerated.

        Returns:
            True if embedding should be updated
        """
        if self.embedding is None:
            return True
        if self.embedding_updated is None:
            return True
        if self.updated and self.updated > self.embedding_updated:
            return True
        return False


@event.listens_for(Mark, 'before_insert')
def receive_before_insert(
    mapper: Any,
    connection: Any,
    target: Mark
) -> None:
    """Event listener for before insert - placeholder for future use."""
    pass


# Note: search_vector is a PostgreSQL generated column, updated automatically by the database.
# See migration: migrations/versions/be4a02ad2b40_adding_create_after_triger_for_full_.py


@event.listens_for(Mark.__table__, 'after_create')
def receive_after_create(
    target: Any,
    connection: Any,
    **kwargs: Any
) -> None:
    """
    Event listener for after table creation.

    Note: Fulltext index is created via migrations.
    See: migrations/versions/be4a02ad2b40_adding_create_after_triger_for_full_.py
    """
    pass
