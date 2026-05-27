"""create delivery_queue table

Revision ID: 6d6e7f8a9b0c
Revises: 5d5e6f7a8b9c
Create Date: 2026-05-27 03:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6d6e7f8a9b0c'
down_revision = '5d5e6f7a8b9c'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'delivery_queue',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('activity_id', sa.Integer(), nullable=False),
        sa.Column('inbox_url', sa.Unicode(length=512), nullable=False),
        sa.Column('status', sa.Unicode(length=20), nullable=False, server_default='pending'),
        sa.Column('retries', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created', sa.DateTime(), nullable=False, server_default=sa.text('(datetime(\'now\'))')),
        sa.Column('updated', sa.DateTime(), nullable=False, server_default=sa.text('(datetime(\'now\'))')),
        sa.ForeignKeyConstraint(['activity_id'], ['activities.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('delivery_queue', schema=None) as batch_op:
        batch_op.create_index('ix_delivery_queue_status_created', ['status', 'created'])
        batch_op.create_index('ix_delivery_queue_activity', ['activity_id'])


def downgrade():
    with op.batch_alter_table('delivery_queue', schema=None) as batch_op:
        batch_op.drop_index('ix_delivery_queue_activity')
        batch_op.drop_index('ix_delivery_queue_status_created')
    op.drop_table('delivery_queue')