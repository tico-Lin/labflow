"""v0.3 add reasoning and script tables

Revision ID: 551dc73b75e5
Revises: 22d679eda916
Create Date: 2026-02-14 22:00:47.552643

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy_utils import UUIDType

# revision identifiers, used by Alembic.
revision: str = '551dc73b75e5'
down_revision: Union[str, Sequence[str], None] = '22d679eda916'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add v0.3 reasoning and script tables."""
    # 推理鏈表
    op.create_table('reasoning_chains',
        sa.Column('id', UUIDType(binary=False), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('nodes', sa.JSON(), nullable=False),
        sa.Column('is_template', sa.Integer(), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_reasoning_chain_created', 'reasoning_chains', ['created_at'], unique=False)
    op.create_index('idx_reasoning_chain_name', 'reasoning_chains', ['name'], unique=False)
    op.create_index('idx_reasoning_chain_template', 'reasoning_chains', ['is_template'], unique=False)
    
    # 推理執行記錄表
    op.create_table('reasoning_executions',
        sa.Column('id', UUIDType(binary=False), nullable=False),
        sa.Column('chain_id', UUIDType(binary=False), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('input_data', sa.JSON(), nullable=True),
        sa.Column('results', sa.JSON(), nullable=True),
        sa.Column('error_log', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('execution_time_ms', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['chain_id'], ['reasoning_chains.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_execution_chain_status', 'reasoning_executions', ['chain_id', 'status'], unique=False)
    op.create_index('idx_execution_started', 'reasoning_executions', ['started_at'], unique=False)
    op.create_index('idx_execution_status', 'reasoning_executions', ['status'], unique=False)
    
    # 腳本表
    op.create_table('scripts',
        sa.Column('id', UUIDType(binary=False), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('parameters', sa.JSON(), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('version', sa.String(length=20), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_script_category', 'scripts', ['category'], unique=False)
    op.create_index('idx_script_created', 'scripts', ['created_at'], unique=False)
    op.create_index('idx_script_name', 'scripts', ['name'], unique=False)
    
    # 腳本執行記錄表
    op.create_table('script_executions',
        sa.Column('id', UUIDType(binary=False), nullable=False),
        sa.Column('script_id', UUIDType(binary=False), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('input_params', sa.JSON(), nullable=True),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('execution_time_ms', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['script_id'], ['scripts.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_script_exec_script_status', 'script_executions', ['script_id', 'status'], unique=False)
    op.create_index('idx_script_exec_started', 'script_executions', ['started_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_script_exec_started', table_name='script_executions')
    op.drop_index('idx_script_exec_script_status', table_name='script_executions')
    op.drop_table('script_executions')
    
    op.drop_index('idx_script_name', table_name='scripts')
    op.drop_index('idx_script_created', table_name='scripts')
    op.drop_index('idx_script_category', table_name='scripts')
    op.drop_table('scripts')
    
    op.drop_index('idx_execution_status', table_name='reasoning_executions')
    op.drop_index('idx_execution_started', table_name='reasoning_executions')
    op.drop_index('idx_execution_chain_status', table_name='reasoning_executions')
    op.drop_table('reasoning_executions')
    
    op.drop_index('idx_reasoning_chain_template', table_name='reasoning_chains')
    op.drop_index('idx_reasoning_chain_name', table_name='reasoning_chains')
    op.drop_index('idx_reasoning_chain_created', table_name='reasoning_chains')
    op.drop_table('reasoning_chains')
