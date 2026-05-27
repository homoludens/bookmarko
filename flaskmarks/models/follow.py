"""
Follow model for tracking user follow relationships.
"""
from __future__ import annotations

from datetime import datetime as dt

from flaskmarks.core.extensions import db


class Follow(db.Model):
    """Track follow relationships between users (local and remote)."""
    __tablename__ = 'follows'

    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    remote_actor_id = db.Column(db.Unicode(512), nullable=True)
    remote_inbox_url = db.Column(db.Unicode(512), nullable=True)
    status = db.Column(db.Unicode(20), nullable=False, default='accepted')
    created = db.Column(db.DateTime, nullable=False, default=dt.utcnow)
    updated = db.Column(db.DateTime, nullable=False, default=dt.utcnow, onupdate=dt.utcnow)

    follower = db.relationship('User', foreign_keys=[follower_id], backref=db.backref('following', lazy='dynamic'))
    followed = db.relationship('User', foreign_keys=[followed_id], backref=db.backref('followers', lazy='dynamic'))

    __table_args__ = (
        db.Index('ix_follows_follower_followed', 'follower_id', 'followed_id'),
    )

    def __repr__(self):
        return (
            f'<Follow {self.follower_id} -> {self.followed_id or self.remote_actor_id} '
            f'[{self.status}]>'
        )