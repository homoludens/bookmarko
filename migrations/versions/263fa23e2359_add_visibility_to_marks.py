"""add visibility to marks

Revision ID: 263fa23e2359
Revises: 9c1d62d0d7bf
Create Date: 2026-05-27 01:32:32.297035

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '263fa23e2359'
down_revision = '9c1d62d0d7bf'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('marks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('visibility', sa.Unicode(length=20), nullable=False, server_default='private'))


def downgrade():
    with op.batch_alter_table('marks', schema=None) as batch_op:
        batch_op.drop_column('visibility')