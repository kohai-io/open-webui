"""add flow execution table

Revision ID: a2c5b3d7e4f8
Revises: e1f4a2b6c3d7
Create Date: 2025-10-18 18:43:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a2c5b3d7e4f8'
down_revision = 'e1f4a2b6c3d7'
branch_labels = None
depends_on = None


def upgrade():
    # Create flow_execution table
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
        sa.Column('meta', sa.JSON(), server_default='{}', nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['flow_id'], ['flow.id'], ondelete='CASCADE')
    )
    
    # Create indexes for performance
    op.create_index(
        'flow_execution_flow_id_created_at_idx',
        'flow_execution',
        ['flow_id', 'created_at']
    )
    op.create_index(
        'flow_execution_user_id_created_at_idx',
        'flow_execution',
        ['user_id', 'created_at']
    )
    op.create_index(
        'flow_execution_flow_id_status_idx',
        'flow_execution',
        ['flow_id', 'status']
    )
    op.create_index(
        'flow_execution_status_idx',
        'flow_execution',
        ['status']
    )


def downgrade():
    # Drop indexes first
    op.drop_index('flow_execution_status_idx', table_name='flow_execution')
    op.drop_index('flow_execution_flow_id_status_idx', table_name='flow_execution')
    op.drop_index('flow_execution_user_id_created_at_idx', table_name='flow_execution')
    op.drop_index('flow_execution_flow_id_created_at_idx', table_name='flow_execution')
    
    # Drop table (foreign key constraint drops automatically)
    op.drop_table('flow_execution')
