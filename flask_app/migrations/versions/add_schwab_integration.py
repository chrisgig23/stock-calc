"""Add Schwab integration: schwab_tokens table + schwab_account_hash on accounts

Revision ID: add_schwab_integration
Revises:
Create Date: 2026-03-30
"""
from alembic import op
import sqlalchemy as sa

revision = 'add_schwab_integration'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add schwab_account_hash column to accounts table
    with op.batch_alter_table('accounts') as batch_op:
        batch_op.add_column(
            sa.Column('schwab_account_hash', sa.String(128), nullable=True)
        )

    # Create schwab_tokens table
    op.create_table(
        'schwab_tokens',
        sa.Column('id',                   sa.Integer,  primary_key=True),
        sa.Column('user_id',              sa.Integer,  sa.ForeignKey('users.id'),
                  nullable=False, unique=True),
        sa.Column('access_token',         sa.Text,     nullable=False),
        sa.Column('refresh_token',        sa.Text,     nullable=False),
        sa.Column('id_token',             sa.Text,     nullable=True),
        sa.Column('access_token_issued',  sa.DateTime, nullable=False),
        sa.Column('refresh_token_issued', sa.DateTime, nullable=False),
    )


def downgrade():
    op.drop_table('schwab_tokens')
    with op.batch_alter_table('accounts') as batch_op:
        batch_op.drop_column('schwab_account_hash')
