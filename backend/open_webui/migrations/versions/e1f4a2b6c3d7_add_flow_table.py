"""Add flow table

Revision ID: e1f4a2b6c3d7
Revises: 018012973d35
Create Date: 2025-10-18 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "e1f4a2b6c3d7"
down_revision = "018012973d35"
branch_labels = None
depends_on = None


def upgrade():
    # Create flow table
    op.create_table(
        "flow",
        sa.Column("id", sa.String(), nullable=False, primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("nodes", sa.JSON(), nullable=False),
        sa.Column("edges", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.Column("meta", sa.JSON(), server_default="{}"),
    )
    
    # Create indexes for flow table
    op.create_index("flow_user_id_idx", "flow", ["user_id"])
    op.create_index("flow_updated_at_idx", "flow", ["updated_at"])
    op.create_index("flow_user_id_updated_at_idx", "flow", ["user_id", "updated_at"])


def downgrade():
    # Drop indexes
    op.drop_index("flow_user_id_idx", table_name="flow")
    op.drop_index("flow_updated_at_idx", table_name="flow")
    op.drop_index("flow_user_id_updated_at_idx", table_name="flow")
    
    # Drop table
    op.drop_table("flow")
