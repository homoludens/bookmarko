"""ActivityPub outbound delivery queue handling.

Provides functions to enqueue activities for delivery and process
the delivery queue with rate limiting and retry logic.
"""
from __future__ import annotations

import json
import time
from datetime import datetime as dt
from typing import TYPE_CHECKING

import requests

from flaskmarks.core.extensions import db

if TYPE_CHECKING:
    from flask import Flask

# In-memory rate limiting: track last request time per domain
_domain_last_request: dict[str, float] = {}

# Rate limit: minimum seconds between requests to the same domain
RATE_LIMIT_SECONDS = 1.0

# Maximum retries for delivery
DEFAULT_MAX_RETRIES = 5


def _get_domain(inbox_url: str) -> str:
    """Extract the domain from an inbox URL for rate limiting."""
    from urllib.parse import urlparse
    parsed = urlparse(inbox_url)
    return parsed.netloc


def _rate_limit_domain(domain: str) -> None:
    """Enforce rate limit for requests to a given domain.

    Blocks until the minimum interval since the last request has elapsed.
    """
    last_time = _domain_last_request.get(domain, 0.0)
    elapsed = time.time() - last_time
    if elapsed < RATE_LIMIT_SECONDS:
        time.sleep(RATE_LIMIT_SECONDS - elapsed)
    _domain_last_request[domain] = time.time()


def enqueue_delivery(activity, inbox_url: str | None = None) -> None:
    """Create a DeliveryQueue entry for an activity to be sent to an inbox.

    Args:
        activity: The Activity model instance to deliver.
        inbox_url: The remote inbox URL. If None, will be resolved from
            the activity's target_id (remote actor URL) later.
    """
    from flaskmarks.models import DeliveryQueue

    if not inbox_url:
        # If no inbox_url provided, skip queue — requires resolution
        return

    delivery = DeliveryQueue(
        activity_id=activity.id,
        inbox_url=inbox_url,
        status='pending',
        retries=0,
        max_retries=DEFAULT_MAX_RETRIES,
        created=dt.utcnow(),
        updated=dt.utcnow(),
    )
    db.session.add(delivery)
    db.session.commit()


def process_delivery_queue(app: Flask, max_items: int = 50) -> int:
    """Process pending deliveries from the queue.

    Args:
        app: Flask application instance (for request context).
        max_items: Maximum number of deliveries to process in one pass.

    Returns:
        Number of deliveries processed.
    """
    from flaskmarks.models import DeliveryQueue, Activity as ActivityModel

    with app.app_context():
        pending = (
            DeliveryQueue.query
            .filter_by(status='pending')
            .order_by(DeliveryQueue.created.asc())
            .limit(max_items)
            .all()
        )

        processed = 0
        for delivery in pending:
            success = _attempt_delivery(delivery)
            processed += 1

        db.session.commit()
        return processed


def _attempt_delivery(delivery) -> bool:
    """Attempt to deliver a single queued activity to its target inbox.

    Returns True if delivery succeeded, False otherwise.
    """
    from flaskmarks.models import DeliveryQueue, Activity as ActivityModel

    activity = ActivityModel.query.get(delivery.activity_id)
    if not activity:
        delivery.status = 'failed'
        delivery.last_error = 'Activity not found'
        return False

    # Build the activity JSON payload
    payload = _build_activity_payload(activity)

    domain = _get_domain(delivery.inbox_url)

    # Enforce rate limiting
    _rate_limit_domain(domain)

    try:
        resp = requests.post(
            delivery.inbox_url,
            data=json.dumps(payload),
            headers={
                'Content-Type': 'application/activity+json',
            },
            timeout=30,
        )

        if resp.status_code in (200, 202, 204):
            delivery.status = 'delivered'
            delivery.updated = dt.utcnow()
            return True
        else:
            raise RuntimeError(
                f'Delivery failed with status {resp.status_code}: '
                f'{resp.text[:200]}'
            )

    except Exception as exc:
        delivery.retries = (delivery.retries or 0) + 1
        delivery.last_error = str(exc)[:500]
        delivery.updated = dt.utcnow()

        if delivery.retries >= (delivery.max_retries or DEFAULT_MAX_RETRIES):
            delivery.status = 'failed'
        else:
            delivery.status = 'pending'

        return False


def _build_activity_payload(activity) -> dict:
    """Build an ActivityPub JSON payload from an Activity model record."""
    payload = {
        '@context': 'https://www.w3.org/ns/activitystreams',
        'type': activity.activity_type,
    }

    # Try to parse stored object_json back to dict
    if activity.object_json:
        try:
            obj = json.loads(activity.object_json)
            payload['object'] = obj
        except (json.JSONDecodeError, TypeError):
            payload['object'] = activity.object_json

    if activity.object_id:
        payload['id'] = activity.object_id

    return payload
