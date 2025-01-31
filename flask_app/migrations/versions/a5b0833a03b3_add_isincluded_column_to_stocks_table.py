"""Add isIncluded column to stocks table

Revision ID: a5b0833a03b3
Revises: 3166704a1e40
Create Date: 2025-01-22 21:32:34.680288

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a5b0833a03b3'
down_revision = '3166704a1e40'
branch_labels = None
depends_on = None


def upgrade():
    # Add the isincluded column to the stocks table with a default value for existing rows
    with op.batch_alter_table('stocks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('isincluded', sa.Boolean(), nullable=False, server_default=sa.text('TRUE')))

    # Optionally remove the server default after setting values for existing rows
    with op.batch_alter_table('stocks', schema=None) as batch_op:
        batch_op.alter_column('isincluded', server_default=None)


def downgrade():
    # Remove the isincluded column from the stocks table
    with op.batch_alter_table('stocks', schema=None) as batch_op:
        batch_op.drop_column('isincluded')