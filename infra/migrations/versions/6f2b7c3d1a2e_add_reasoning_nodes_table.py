"""add reasoning nodes table

Revision ID: 6f2b7c3d1a2e
Revises: 551dc73b75e5
Create Date: 2026-02-15 21:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy_utils import UUIDType

# revision identifiers, used by Alembic.
revision: str = "6f2b7c3d1a2e"
down_revision: Union[str, Sequence[str], None] = "551dc73b75e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add reasoning_nodes table."""
    op.create_table(
        "reasoning_nodes",
        sa.Column("id", UUIDType(binary=False), nullable=False),
        sa.Column("chain_id", UUIDType(binary=False), nullable=False),
        sa.Column("node_id", sa.String(length=128), nullable=False),
        sa.Column("node_type", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.Column("inputs", sa.JSON(), nullable=True),
        sa.Column("outputs", sa.JSON(), nullable=True),
        sa.Column("position", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["chain_id"], ["reasoning_chains.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_reasoning_node_chain_node", "reasoning_nodes", ["chain_id", "node_id"], unique=False)
    op.create_index("idx_reasoning_node_chain_type", "reasoning_nodes", ["chain_id", "node_type"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_reasoning_node_chain_type", table_name="reasoning_nodes")
    op.drop_index("idx_reasoning_node_chain_node", table_name="reasoning_nodes")
    op.drop_table("reasoning_nodes")
