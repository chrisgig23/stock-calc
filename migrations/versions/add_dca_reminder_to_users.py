"""Add DCA reminder columns to users table

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-04-01

"""
from alembic import op
import sqlalchemy as sa

revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users',
        sa.Column('dca_reminder_enabled', sa.Boolean(), nullable=False, server_default='false')
    )
    op.add_column('users',
        sa.Column('dca_reminder_day', sa.Integer(), nullable=True)
    )


def downgrade():
    op.drop_column('users', 'dca_reminder_day')
    op.drop_column('users', 'dca_reminder_enabled')
