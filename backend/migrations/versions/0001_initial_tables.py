"""initial tables

Revision ID: 0001
Revises: 
"""
from alembic import op
import sqlalchemy as sa


revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('usage_counters',
    sa.Column('subject', sa.String(length=40), nullable=False),
    sa.Column('day', sa.String(length=10), nullable=False),
    sa.Column('kind', sa.String(length=20), nullable=False),
    sa.Column('count', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('subject', 'day', 'kind')
    )
    op.create_table('users',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('created_at', sa.BigInteger(), nullable=False),
    sa.Column('signup_ip_hash', sa.String(length=32), nullable=False),
    sa.Column('email_hash', sa.String(length=64), nullable=True),
    sa.Column('verified_at', sa.BigInteger(), nullable=True),
    sa.Column('token_version', sa.Integer(), nullable=False),
    sa.Column('blocked', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email_hash')
    )
    op.create_index(op.f('ix_users_signup_ip_hash'), 'users', ['signup_ip_hash'], unique=False)
    op.create_table('email_challenges',
    sa.Column('user_id', sa.String(length=32), nullable=False),
    sa.Column('email_hash', sa.String(length=64), nullable=False),
    sa.Column('code_hash', sa.String(length=64), nullable=False),
    sa.Column('ip_hash', sa.String(length=32), nullable=False),
    sa.Column('created_at', sa.BigInteger(), nullable=False),
    sa.Column('expires_at', sa.BigInteger(), nullable=False),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id')
    )
    op.create_index(op.f('ix_email_challenges_ip_hash'), 'email_challenges', ['ip_hash'], unique=False)
    op.create_table('number_reports',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('number', sa.String(length=13), nullable=False),
    sa.Column('user_id', sa.String(length=32), nullable=False),
    sa.Column('ip_hash', sa.String(length=32), nullable=False),
    sa.Column('note', sa.String(length=280), nullable=False),
    sa.Column('created_at', sa.BigInteger(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('number', 'user_id', name='uq_report_number_user')
    )
    op.create_index(op.f('ix_number_reports_number'), 'number_reports', ['number'], unique=False)
    op.create_index(op.f('ix_number_reports_user_id'), 'number_reports', ['user_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_number_reports_user_id'), table_name='number_reports')
    op.drop_index(op.f('ix_number_reports_number'), table_name='number_reports')
    op.drop_table('number_reports')
    op.drop_index(op.f('ix_email_challenges_ip_hash'), table_name='email_challenges')
    op.drop_table('email_challenges')
    op.drop_index(op.f('ix_users_signup_ip_hash'), table_name='users')
    op.drop_table('users')
    op.drop_table('usage_counters')
