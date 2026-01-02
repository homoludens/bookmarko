"""Background tasks for RAG processing."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Queue for pending embedding updates (simple in-memory for now)
_pending_updates: set[int] = set()


def queue_embedding_update(mark_id: int) -> None:
    """
    Queue a mark for embedding update.

    For production, this should use Celery or similar.
    For now, we use a simple in-memory queue processed by CLI.
    """
    _pending_updates.add(mark_id)
    logger.debug(f"Queued embedding update for mark {mark_id}")


def get_pending_updates() -> set[int]:
    """Get all pending mark IDs for embedding updates."""
    return _pending_updates.copy()


def clear_pending_updates() -> None:
    """Clear the pending updates queue."""
    _pending_updates.clear()


def process_pending_embeddings(app) -> tuple[int, int]:
    """
    Process all pending embedding updates.

    Args:
        app: Flask application instance

    Returns:
        Tuple of (successful, failed) counts
    """
    from flaskmarks.models import Mark
    from .embeddings import EmbeddingService

    pending = get_pending_updates()
    if not pending:
        return 0, 0

    embedding_service = EmbeddingService()
    successful = 0
    failed = 0

    with app.app_context():
        for mark_id in pending:
            mark = Mark.query.get(mark_id)
            if mark:
                if embedding_service.update_mark_embedding(mark):
                    successful += 1
                else:
                    failed += 1

    clear_pending_updates()
    return successful, failed
