"""Add access_control to flow table

Revision ID: f3a8b2c1d4e5
Revises: a2c5b3d7e4f8
Create Date: 2025-01-31 16:50:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "f3a8b2c1d4e5"
down_revision = "a2c5b3d7e4f8"
branch_labels = None
depends_on = None


def upgrade():
    # Add access_control column to flow table
    # - None: Public access, available to all users with the "user" role
    # - {}: Private access, restricted exclusively to the owner
    # - Custom permissions: {read: {group_ids: [], user_ids: []}, write: {...}}
    op.add_column(
        "flow",
        sa.Column("access_control", sa.JSON(), nullable=True),
    )


def downgrade():
    op.drop_column("flow", "access_control")
