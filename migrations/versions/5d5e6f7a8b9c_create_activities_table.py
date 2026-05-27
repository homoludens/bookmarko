"""create activities table

Revision ID: 5d5e6f7a8b9c
Revises: 4c4e5f6a7b8c
Create Date: 2026-05-27 02:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5d5e6f7a8b9c'
down_revision = '4c4e5f6a7b8c'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'activities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('actor_id', sa.Integer(), nullable=False),
        sa.Column('activity_type', sa.Unicode(length=50), nullable=False),
        sa.Column('object_json', sa.Text(), nullable=True),
        sa.Column('object_id', sa.Unicode(length=512), nullable=True),
        sa.Column('target_id', sa.Unicode(length=512), nullable=True),
        sa.Column('created', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('activities', schema=None) as batch_op:
        batch_op.create_index('ix_activities_actor_type', ['actor_id', 'activity_type'])
        batch_op.create_index(batch_op.f('ix_activities_created'), ['created'])


def downgrade():
    with op.batch_alter_table('activities', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_activities_created'))
        batch_op.drop_index('ix_activities_actor_type')
    op.drop_table('activities')