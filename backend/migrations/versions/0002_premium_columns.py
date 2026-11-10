"""premium columns on users

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa


revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade():
    # Dono NULL ho sakte hain — purane sab users free plan par shuru hote hain.
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('premium_until', sa.BigInteger(), nullable=True))
        batch_op.add_column(sa.Column('premium_checked_at', sa.BigInteger(), nullable=True))


def downgrade():
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('premium_checked_at')
        batch_op.drop_column('premium_until')
