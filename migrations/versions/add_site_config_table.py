"""add site_config table

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-04-06
"""
from alembic import op
import sqlalchemy as sa

revision = 'e5f6a7b8c9d0'
down_revision = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'site_config',
        sa.Column('key',   sa.String(64),  primary_key=True),
        sa.Column('value', sa.String(255), nullable=True),
    )


def downgrade():
    op.drop_table('site_config')
