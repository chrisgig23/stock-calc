"""Add email verification columns to users table

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-03-31

"""
from alembic import op
import sqlalchemy as sa

revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users',
        sa.Column('email', sa.String(255), nullable=True)
    )
    op.add_column('users',
        sa.Column('email_verified', sa.Boolean(), nullable=False, server_default='false')
    )
    op.add_column('users',
        sa.Column('email_verification_code', sa.String(6), nullable=True)
    )
    op.add_column('users',
        sa.Column('email_code_expires', sa.DateTime(), nullable=True)
    )
    op.create_unique_constraint('uq_users_email', 'users', ['email'])


def downgrade():
    op.drop_constraint('uq_users_email', 'users', type_='unique')
    op.drop_column('users', 'email_code_expires')
    op.drop_column('users', 'email_verification_code')
    op.drop_column('users', 'email_verified')
    op.drop_column('users', 'email')
