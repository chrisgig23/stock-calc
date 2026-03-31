"""Add is_admin column to users table

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-03-31

"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add is_admin column — existing rows default to False
    op.add_column('users',
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false')
    )
    # Grant admin to the primary admin user
    op.execute("UPDATE users SET is_admin = true WHERE username = 'cgiglio'")


def downgrade():
    op.drop_column('users', 'is_admin')
