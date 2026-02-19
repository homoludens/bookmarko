"""add import job status persistence table

Revision ID: c4f6f8b1d2aa
Revises: fb1d465c762b
Create Date: 2026-02-19 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c4f6f8b1d2aa"
down_revision = "fb1d465c762b"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "import_job_statuses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Unicode(length=64), nullable=False),
        sa.Column("status", sa.Integer(), nullable=False),
        sa.Column("total_lines", sa.Integer(), nullable=False),
        sa.Column("complete", sa.Boolean(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("updated", sa.DateTime(), nullable=False),
        sa.Column("completed", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "job_id", name="uq_import_job_status_user_job"),
    )
    op.create_index(
        "ix_import_job_status_user_updated",
        "import_job_statuses",
        ["user_id", "updated"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_import_job_status_user_updated", table_name="import_job_statuses")
    op.drop_table("import_job_statuses")
