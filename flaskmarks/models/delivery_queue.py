"""
DeliveryQueue model for tracking outbound ActivityPub delivery status.
"""
from __future__ import annotations

from datetime import datetime as dt

from flaskmarks.core.extensions import db


class DeliveryQueue(db.Model):
    """Track delivery of outgoing ActivityPub activities to remote inboxes."""
    __tablename__ = 'delivery_queue'

    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(db.Integer, db.ForeignKey('activities.id'), nullable=False, index=True)
    inbox_url = db.Column(db.Unicode(512), nullable=False)
    status = db.Column(db.Unicode(20), nullable=False, default='pending')
    retries = db.Column(db.Integer, nullable=False, default=0)
    max_retries = db.Column(db.Integer, nullable=False, default=5)
    last_error = db.Column(db.Text, nullable=True)
    created = db.Column(db.DateTime, nullable=False, default=dt.utcnow)
    updated = db.Column(db.DateTime, nullable=False, default=dt.utcnow, onupdate=dt.utcnow)

    activity = db.relationship('Activity', backref=db.backref('deliveries', lazy='dynamic'))

    __table_args__ = (
        db.Index('ix_delivery_queue_status_created', 'status', 'created'),
        db.Index('ix_delivery_queue_activity', 'activity_id'),
    )

    def __repr__(self):
        return f'<DeliveryQueue activity={self.activity_id} status={self.status} retries={self.retries}>'