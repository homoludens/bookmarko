"""
Service helpers for user/job-scoped import status persistence.
"""
from __future__ import annotations

from datetime import datetime as dt

from flaskmarks.core.extensions import db
from flaskmarks.models.import_job_status import ImportJobStatus


DEFAULT_IMPORT_JOB_ID = "default"


def create_or_reset_import_job(
    user_id: int,
    job_id: str | None,
    total_lines: int = 0,
) -> ImportJobStatus:
    """Create or reset scoped import status."""
    scope_job_id = job_id or DEFAULT_IMPORT_JOB_ID
    job = ImportJobStatus.query.filter_by(
        user_id=user_id,
        job_id=scope_job_id,
    ).first()
    if job is None:
        job = ImportJobStatus(user_id=user_id, job_id=scope_job_id)
        db.session.add(job)

    job.status = 0
    job.total_lines = max(0, total_lines)
    job.complete = False
    job.completed = None
    db.session.commit()
    return job


def increment_import_job_status(
    user_id: int,
    job_id: str | None,
    increment: int = 1,
) -> ImportJobStatus | None:
    """Increment progress for a scoped import job."""
    scope_job_id = job_id or DEFAULT_IMPORT_JOB_ID
    job = ImportJobStatus.query.filter_by(
        user_id=user_id,
        job_id=scope_job_id,
    ).first()
    if job is None:
        return None

    if increment > 0:
        next_value = job.status + increment
        if job.total_lines > 0:
            next_value = min(next_value, job.total_lines)
        job.status = next_value
        db.session.commit()
    return job


def complete_import_job(user_id: int, job_id: str | None) -> ImportJobStatus | None:
    """Mark scoped import job as complete."""
    scope_job_id = job_id or DEFAULT_IMPORT_JOB_ID
    job = ImportJobStatus.query.filter_by(
        user_id=user_id,
        job_id=scope_job_id,
    ).first()
    if job is None:
        return None

    job.complete = True
    job.completed = dt.utcnow()
    if job.total_lines > 0:
        job.status = min(job.status, job.total_lines)
    db.session.commit()
    return job


def get_import_job_status(
    user_id: int,
    job_id: str | None = None,
) -> ImportJobStatus | None:
    """Get scoped job status, or the latest for a user when scope is omitted."""
    query = ImportJobStatus.query.filter_by(user_id=user_id)
    if job_id:
        return query.filter_by(job_id=job_id).first()

    return query.order_by(ImportJobStatus.updated.desc()).first()
