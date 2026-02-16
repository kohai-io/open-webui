"""Add function_calling_mode to scheduled_prompt

Revision ID: h1j2k3l4m5n6
Revises: g4h5i6j7k8l9
Create Date: 2026-02-16

"""

from alembic import op
import sqlalchemy as sa


revision = "h1j2k3l4m5n6"
down_revision = "g4h5i6j7k8l9"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("scheduled_prompt")]

    if "function_calling_mode" not in columns:
        op.add_column(
            "scheduled_prompt",
            sa.Column(
                "function_calling_mode",
                sa.String(),
                nullable=False,
                server_default="default",
            ),
        )


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("scheduled_prompt")]

    if "function_calling_mode" in columns:
        op.drop_column("scheduled_prompt", "function_calling_mode")
