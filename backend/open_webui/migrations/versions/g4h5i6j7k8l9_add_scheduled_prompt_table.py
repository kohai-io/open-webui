"""Add scheduled_prompt table

Revision ID: g4h5i6j7k8l9
Revises: f3a8b2c1d4e5
Create Date: 2026-02-03

"""

from alembic import op
import sqlalchemy as sa

revision = "g4h5i6j7k8l9"
down_revision = "f3a8b2c1d4e5"
branch_labels = None
depends_on = None


def upgrade():
    # Check if table already exists (for existing installations)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    if "scheduled_prompt" not in tables:
        op.create_table(
            "scheduled_prompt",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("cron_expression", sa.String(), nullable=False),
            sa.Column("timezone", sa.String(), default="UTC"),
            sa.Column("enabled", sa.Boolean(), default=True),
            sa.Column("model_id", sa.String(), nullable=False),
            sa.Column("system_prompt", sa.Text(), nullable=True),
            sa.Column("prompt", sa.Text(), nullable=False),
            sa.Column("chat_id", sa.String(), nullable=True),
            sa.Column("create_new_chat", sa.Boolean(), default=True),
            sa.Column("run_once", sa.Boolean(), default=False),
            sa.Column("tool_ids", sa.JSON(), nullable=True),
            sa.Column("last_run_at", sa.BigInteger(), nullable=True),
            sa.Column("next_run_at", sa.BigInteger(), nullable=True),
            sa.Column("last_status", sa.String(), nullable=True),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("run_count", sa.Integer(), default=0),
            sa.Column("created_at", sa.BigInteger()),
            sa.Column("updated_at", sa.BigInteger()),
        )
        op.create_index("scheduled_prompt_user_id_idx", "scheduled_prompt", ["user_id"])
        op.create_index("scheduled_prompt_enabled_next_run_idx", "scheduled_prompt", ["enabled", "next_run_at"])
        op.create_index("scheduled_prompt_user_id_enabled_idx", "scheduled_prompt", ["user_id", "enabled"])
    else:
        # Table exists, check for missing columns
        columns = [col["name"] for col in inspector.get_columns("scheduled_prompt")]
        if "run_once" not in columns:
            op.add_column(
                "scheduled_prompt",
                sa.Column("run_once", sa.Boolean(), nullable=True, default=False),
            )
            op.execute("UPDATE scheduled_prompt SET run_once = 0 WHERE run_once IS NULL")
        if "tool_ids" not in columns:
            op.add_column(
                "scheduled_prompt",
                sa.Column("tool_ids", sa.JSON(), nullable=True),
            )


def downgrade():
    op.drop_table("scheduled_prompt")
