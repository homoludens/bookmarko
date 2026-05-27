"""Celery tasks for ActivityPub federation operations.

Provides background tasks for delivering activities, retrying failed
deliveries, and cleaning up old activity records.
"""
from __future__ import annotations

from datetime import datetime as dt, timedelta

from celery import Celery

from flaskmarks.core.extensions import db

# Celery app instance - configure via CELERY_BROKER_URL in Flask config
celery = Celery('flaskmarks')
celery.config_from_object('celeryconfig')


@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def deliver_activity(self, activity_id: int, inbox_url: str) -> str:
    """Deliver a single activity to a remote inbox.

    This task wraps the processing of a single delivery queue entry.

    Args:
        activity_id: ID of the Activity record.
        inbox_url: Target remote inbox URL.

    Returns:
        Status string ('delivered', 'pending', or 'failed').
    """
    from flaskmarks.core.activitypub_delivery import process_delivery_queue
    from flaskmarks.core.extensions import db
    from flaskmarks import create_app

    app = create_app()
    with app.app_context():
        try:
            processed = process_delivery_queue(app, max_items=10)
            return 'delivered' if processed > 0 else 'failed'
        except Exception as exc:
            raise self.retry(exc=exc)


@celery.task(bind=True, max_retries=3, default_retry_delay=300)
def retry_failed_deliveries(self) -> dict:
    """Retry all failed and pending deliveries.

    Finds all delivery queue entries with status 'pending' or 'failed'
    and attempts to re-process them through the delivery pipeline.

    Returns:
        Dict with counts of retried and remaining entries.
    """
    from flaskmarks.core.activitypub_delivery import process_delivery_queue
    from flaskmarks.models import DeliveryQueue
    from flaskmarks import create_app

    app = create_app()
    with app.app_context():
        try:
            count_before = DeliveryQueue.query.filter(
                DeliveryQueue.status.in_(['pending', 'failed'])
            ).count()

            processed = process_delivery_queue(app, max_items=100)

            count_after = DeliveryQueue.query.filter(
                DeliveryQueue.status.in_(['pending', 'failed'])
            ).count()

            return {
                'retried': processed,
                'remaining': count_after,
                'delivered': count_before - count_after,
            }
        except Exception as exc:
            raise self.retry(exc=exc)


@celery.task
def cleanup_old_activities(days: int = 90) -> int:
    """Purge delivered activity records older than the specified number of days.

    Args:
        days: Age threshold in days (default 90). Activities older than
            this and in 'delivered' status will be removed.

    Returns:
        Number of records purged.
    """
    from flaskmarks.models import DeliveryQueue
    from flaskmarks import create_app

    app = create_app()
    with app.app_context():
        cutoff = dt.utcnow() - timedelta(days=days)

        old_deliveries = DeliveryQueue.query.filter(
            DeliveryQueue.status == 'delivered',
            DeliveryQueue.created < cutoff,
        ).all()

        count = len(old_deliveries)
        for delivery in old_deliveries:
            db.session.delete(delivery)

        db.session.commit()
        return count
