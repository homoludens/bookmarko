"""add indexes for tag aggregation query path

Revision ID: 9c1d62d0d7bf
Revises: c4f6f8b1d2aa
Create Date: 2026-02-19 00:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "9c1d62d0d7bf"
down_revision = "c4f6f8b1d2aa"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index("ix_marks_owner_id", "marks", ["owner_id"], unique=False)
    op.create_index("ix_marks_tags_left_id", "marks_tags", ["left_id"], unique=False)
    op.create_index("ix_marks_tags_right_id", "marks_tags", ["right_id"], unique=False)
    op.create_index(
        "ix_marks_tags_left_right",
        "marks_tags",
        ["left_id", "right_id"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_marks_tags_left_right", table_name="marks_tags")
    op.drop_index("ix_marks_tags_right_id", table_name="marks_tags")
    op.drop_index("ix_marks_tags_left_id", table_name="marks_tags")
    op.drop_index("ix_marks_owner_id", table_name="marks")
