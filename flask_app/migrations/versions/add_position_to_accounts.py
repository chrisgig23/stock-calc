"""
Add position column to accounts table
"""
# revision identifiers, used by Alembic.
revision = 'f4a8b7c6d5e4'  # Using a proper format revision ID
down_revision = '3166704a1e40'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('accounts', sa.Column('position', sa.Integer(), nullable=False, server_default='0'))
    op.alter_column('accounts', 'position', server_default=None)

def downgrade():
    op.drop_column('accounts', 'position')
