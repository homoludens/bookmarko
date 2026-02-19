"""
Persisted import job status model scoped by user and job id.
"""
from __future__ import annotations

from datetime import datetime as dt

from flaskmarks.core.extensions import db


class ImportJobStatus(db.Model):
    """
    Track bookmark import progress for a specific user/job pair.
    """
    __tablename__ = "import_job_statuses"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    job_id = db.Column(db.Unicode(64), nullable=False)
    status = db.Column(db.Integer, nullable=False, default=0)
    total_lines = db.Column(db.Integer, nullable=False, default=0)
    complete = db.Column(db.Boolean, nullable=False, default=False)
    created = db.Column(db.DateTime, nullable=False, default=dt.utcnow)
    updated = db.Column(
        db.DateTime,
        nullable=False,
        default=dt.utcnow,
        onupdate=dt.utcnow,
    )
    completed = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        db.UniqueConstraint("user_id", "job_id", name="uq_import_job_status_user_job"),
        db.Index("ix_import_job_status_user_updated", "user_id", "updated"),
    )

    def as_dict(self) -> dict[str, int | bool | str | None]:
        """Serialize to the existing endpoint response shape."""
        return {
            "job_id": self.job_id,
            "status": self.status,
            "total_lines": self.total_lines,
            "complete": self.complete,
        }
