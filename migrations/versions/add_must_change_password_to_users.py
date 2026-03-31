"""Add must_change_password column to users table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-31

"""
from alembic import op
import sqlalchemy as sa

revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    # Add must_change_password column — all existing users default to False
    op.add_column('users',
        sa.Column('must_change_password', sa.Boolean(), nullable=False, server_default='false')
    )


def downgrade():
    op.drop_column('users', 'must_change_password')
