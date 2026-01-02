"""add embedding column for RAG

Revision ID: a1b2c3d4e5f6
Revises: 3da329c515c1
Create Date: 2026-01-02

"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '3da329c515c1'
branch_labels = None
depends_on = None


def upgrade():
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # Add embedding column (384 dimensions for all-MiniLM-L6-v2)
    with op.batch_alter_table('marks', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('embedding', Vector(384), nullable=True)
        )
        batch_op.add_column(
            sa.Column('embedding_updated', sa.DateTime(), nullable=True)
        )

    # Create IVFFlat index for fast similarity search
    # Note: IVFFlat requires the table to have some data for optimal list count
    # For small datasets, use HNSW or no index
    op.execute(
        'CREATE INDEX idx_marks_embedding ON marks '
        'USING hnsw (embedding vector_cosine_ops)'
    )


def downgrade():
    op.execute('DROP INDEX IF EXISTS idx_marks_embedding')

    with op.batch_alter_table('marks', schema=None) as batch_op:
        batch_op.drop_column('embedding_updated')
        batch_op.drop_column('embedding')
