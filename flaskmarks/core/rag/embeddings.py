"""Embedding service for generating and storing mark embeddings."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional, Callable

from flask import current_app

if TYPE_CHECKING:
    from flaskmarks.models import Mark

# Global model instance (lazy loaded)
_embedding_model = None


def get_embedding_model():
    """Get or initialize the embedding model (singleton)."""
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        model_name = current_app.config.get(
            'EMBEDDING_MODEL',
            'sentence-transformers/all-MiniLM-L6-v2'
        )
        _embedding_model = SentenceTransformer(model_name)
    return _embedding_model


class EmbeddingService:
    """Service for managing mark embeddings."""

    def __init__(self):
        self.model = None

    def _get_model(self):
        """Lazy load the embedding model."""
        if self.model is None:
            self.model = get_embedding_model()
        return self.model

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding
        """
        model = self._get_model()
        embedding = model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def update_mark_embedding(self, mark: 'Mark') -> bool:
        """
        Update embedding for a single mark.

        Uses raw SQL to avoid triggering the search_vector update listener.

        Args:
            mark: Mark instance to update

        Returns:
            True if successful, False otherwise
        """
        from flaskmarks.core.extensions import db
        from sqlalchemy import text

        try:
            embedding_text = mark.get_embedding_text()
            embedding = self.generate_embedding(embedding_text)
            now = datetime.utcnow()

            # Use raw SQL to update only embedding columns
            # This avoids triggering the search_vector update
            sql = text("""
                UPDATE marks
                SET embedding = :embedding::vector,
                    embedding_updated = :updated
                WHERE id = :mark_id
            """)

            db.session.execute(sql, {
                'embedding': str(embedding),
                'updated': now,
                'mark_id': mark.id
            })
            db.session.commit()

            # Update the in-memory object too
            mark.embedding = embedding
            mark.embedding_updated = now

            return True
        except Exception as e:
            current_app.logger.error(
                f"Failed to update embedding for mark {mark.id}: {e}"
            )
            db.session.rollback()
            return False

    def batch_update_embeddings(
        self,
        marks: List['Mark'],
        batch_size: int = 32,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> tuple[int, int]:
        """
        Update embeddings for multiple marks in batches.

        Uses raw SQL to avoid triggering the search_vector update listener.

        Args:
            marks: List of Mark instances
            batch_size: Number of marks to process at once
            progress_callback: Optional callback(current, total) for progress

        Returns:
            Tuple of (successful_count, failed_count)
        """
        from flaskmarks.core.extensions import db
        from sqlalchemy import text

        model = self._get_model()
        successful = 0
        failed = 0
        total = len(marks)

        for i in range(0, total, batch_size):
            batch = marks[i:i + batch_size]
            texts = [m.get_embedding_text() for m in batch]

            try:
                embeddings = model.encode(texts, normalize_embeddings=True)
                now = datetime.utcnow()

                # Use raw SQL to update only embedding columns
                # This avoids triggering the search_vector update
                for mark, embedding in zip(batch, embeddings):
                    sql = text("""
                        UPDATE marks
                        SET embedding = :embedding::vector,
                            embedding_updated = :updated
                        WHERE id = :mark_id
                    """)

                    db.session.execute(sql, {
                        'embedding': str(embedding.tolist()),
                        'updated': now,
                        'mark_id': mark.id
                    })

                db.session.commit()
                successful += len(batch)
            except Exception as e:
                current_app.logger.error(f"Batch embedding failed: {e}")
                db.session.rollback()
                failed += len(batch)

            if progress_callback:
                progress_callback(min(i + batch_size, total), total)

        return successful, failed
