"""Add automation run created-at index

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-05-10 15:52:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd3e4f5a6b7c8'
down_revision: Union[str, None] = 'c2d3e4f5a6b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_names() -> set[str]:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    return set(inspector.get_table_names())


def _index_names(table_name: str) -> set[str]:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    return {index['name'] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    if 'automation_run' in _table_names() and 'ix_automation_run_aid_created' not in _index_names('automation_run'):
        op.create_index('ix_automation_run_aid_created', 'automation_run', ['automation_id', 'created_at'])


def downgrade() -> None:
    if 'automation_run' in _table_names() and 'ix_automation_run_aid_created' in _index_names('automation_run'):
        op.drop_index('ix_automation_run_aid_created', table_name='automation_run')
