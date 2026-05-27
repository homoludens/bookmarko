"""create follows table

Revision ID: 4c4e5f6a7b8c
Revises: b1d5662161d2
Create Date: 2026-05-27 01:58:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4c4e5f6a7b8c'
down_revision = 'b1d5662161d2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'follows',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('follower_id', sa.Integer(), nullable=False),
        sa.Column('followed_id', sa.Integer(), nullable=True),
        sa.Column('remote_actor_id', sa.Unicode(length=512), nullable=True),
        sa.Column('remote_inbox_url', sa.Unicode(length=512), nullable=True),
        sa.Column('status', sa.Unicode(length=20), nullable=False, server_default='accepted'),
        sa.Column('created', sa.DateTime(), nullable=False),
        sa.Column('updated', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['follower_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['followed_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('follows', schema=None) as batch_op:
        batch_op.create_index('ix_follows_follower_followed', ['follower_id', 'followed_id'])
        batch_op.create_index(batch_op.f('ix_follows_follower_id'), ['follower_id'])
        batch_op.create_index(batch_op.f('ix_follows_followed_id'), ['followed_id'])


def downgrade():
    with op.batch_alter_table('follows', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_follows_followed_id'))
        batch_op.drop_index(batch_op.f('ix_follows_follower_id'))
        batch_op.drop_index('ix_follows_follower_followed')
    op.drop_table('follows')
