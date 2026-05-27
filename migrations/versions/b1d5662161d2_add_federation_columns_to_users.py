"""add federation columns to users

Revision ID: b1d5662161d2
Revises: 9c1d62d0d7bf
Create Date: 2026-05-27 01:36:55.237393

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b1d5662161d2'
down_revision = '263fa23e2359'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('actor_id', sa.Unicode(length=512), nullable=True))
        batch_op.add_column(sa.Column('private_key_pem', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('public_key_pem', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('inbox_url', sa.Unicode(length=512), nullable=True))
        batch_op.add_column(sa.Column('outbox_url', sa.Unicode(length=512), nullable=True))
        batch_op.add_column(sa.Column('followers_url', sa.Unicode(length=512), nullable=True))
        batch_op.add_column(sa.Column('following_url', sa.Unicode(length=512), nullable=True))
        batch_op.add_column(sa.Column('default_bookmark_visibility', sa.Unicode(length=20), nullable=False, server_default='private'))


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('default_bookmark_visibility')
        batch_op.drop_column('following_url')
        batch_op.drop_column('followers_url')
        batch_op.drop_column('outbox_url')
        batch_op.drop_column('inbox_url')
        batch_op.drop_column('public_key_pem')
        batch_op.drop_column('private_key_pem')
        batch_op.drop_column('actor_id')