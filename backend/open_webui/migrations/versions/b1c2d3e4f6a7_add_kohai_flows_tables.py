"""Add Kohai flows tables

Revision ID: b1c2d3e4f6a7
Revises: a0b1c2d3e4f5
Create Date: 2026-05-10 11:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b1c2d3e4f6a7'
down_revision: Union[str, None] = 'a0b1c2d3e4f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_names():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    return set(inspector.get_table_names())


def _column_names(table_name: str):
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    return {column['name'] for column in inspector.get_columns(table_name)}


def _index_names(table_name: str):
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    return {index['name'] for index in inspector.get_indexes(table_name)}


def _create_index_if_missing(index_name: str, table_name: str, columns: list[str]):
    if index_name not in _index_names(table_name):
        op.create_index(index_name, table_name, columns)


def upgrade() -> None:
    tables = _table_names()

    if 'flow' not in tables:
        op.create_table(
            'flow',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('user_id', sa.String(), nullable=False),
            sa.Column('name', sa.Text(), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('nodes', sa.JSON(), nullable=False),
            sa.Column('edges', sa.JSON(), nullable=False),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
            sa.Column('updated_at', sa.BigInteger(), nullable=False),
            sa.Column('meta', sa.JSON(), nullable=False, server_default='{}'),
            sa.Column('access_control', sa.JSON(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
    else:
        columns = _column_names('flow')
        if 'meta' not in columns:
            op.add_column('flow', sa.Column('meta', sa.JSON(), nullable=False, server_default='{}'))
        if 'access_control' not in columns:
            op.add_column('flow', sa.Column('access_control', sa.JSON(), nullable=True))

    _create_index_if_missing('flow_user_id_idx', 'flow', ['user_id'])
    _create_index_if_missing('flow_updated_at_idx', 'flow', ['updated_at'])
    _create_index_if_missing('flow_user_id_updated_at_idx', 'flow', ['user_id', 'updated_at'])

    tables = _table_names()
    if 'flow_execution' not in tables:
        op.create_table(
            'flow_execution',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('flow_id', sa.String(), nullable=False),
            sa.Column('user_id', sa.String(), nullable=False),
            sa.Column('status', sa.String(), nullable=False),
            sa.Column('inputs', sa.JSON(), nullable=True),
            sa.Column('outputs', sa.JSON(), nullable=True),
            sa.Column('node_results', sa.JSON(), nullable=True),
            sa.Column('errors', sa.JSON(), nullable=True),
            sa.Column('execution_time', sa.BigInteger(), nullable=False),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
            sa.Column('meta', sa.JSON(), nullable=False, server_default='{}'),
            sa.ForeignKeyConstraint(['flow_id'], ['flow.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )
    else:
        columns = _column_names('flow_execution')
        if 'meta' not in columns:
            op.add_column('flow_execution', sa.Column('meta', sa.JSON(), nullable=False, server_default='{}'))

    _create_index_if_missing('flow_execution_flow_id_created_at_idx', 'flow_execution', ['flow_id', 'created_at'])
    _create_index_if_missing('flow_execution_user_id_created_at_idx', 'flow_execution', ['user_id', 'created_at'])
    _create_index_if_missing('flow_execution_flow_id_status_idx', 'flow_execution', ['flow_id', 'status'])
    _create_index_if_missing('flow_execution_status_idx', 'flow_execution', ['status'])


def downgrade() -> None:
    tables = _table_names()
    if 'flow_execution' in tables:
        indexes = _index_names('flow_execution')
        for index_name in [
            'flow_execution_status_idx',
            'flow_execution_flow_id_status_idx',
            'flow_execution_user_id_created_at_idx',
            'flow_execution_flow_id_created_at_idx',
        ]:
            if index_name in indexes:
                op.drop_index(index_name, table_name='flow_execution')
        op.drop_table('flow_execution')

    tables = _table_names()
    if 'flow' in tables:
        indexes = _index_names('flow')
        for index_name in [
            'flow_user_id_updated_at_idx',
            'flow_updated_at_idx',
            'flow_user_id_idx',
        ]:
            if index_name in indexes:
                op.drop_index(index_name, table_name='flow')
        op.drop_table('flow')
