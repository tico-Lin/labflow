"""add reasoning execution metadata

Revision ID: b1c2d3e4f5a6
Revises: 6f2b7c3d1a2e
Create Date: 2026-02-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "6f2b7c3d1a2e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add metadata columns to reasoning_executions."""
    conn = op.get_bind()

    def column_exists(table: str, column: str) -> bool:
        rows = conn.execute(sa.text(f"PRAGMA table_info({table})")).fetchall()
        return column in [row[1] for row in rows]

    def index_exists(table: str, index_name: str) -> bool:
        rows = conn.execute(sa.text(f"PRAGMA index_list({table})")).fetchall()
        return index_name in [row[1] for row in rows]

    if not column_exists("reasoning_executions", "user_id"):
        op.add_column("reasoning_executions", sa.Column("user_id", sa.Integer(), nullable=True))
    if not column_exists("reasoning_executions", "model_name"):
        op.add_column("reasoning_executions", sa.Column("model_name", sa.String(length=100), nullable=True))
    if not column_exists("reasoning_executions", "tool_name"):
        op.add_column("reasoning_executions", sa.Column("tool_name", sa.String(length=100), nullable=True))

    if not index_exists("reasoning_executions", "ix_reasoning_executions_user_id"):
        op.create_index("ix_reasoning_executions_user_id", "reasoning_executions", ["user_id"], unique=False)
    if not index_exists("reasoning_executions", "ix_reasoning_executions_model_name"):
        op.create_index("ix_reasoning_executions_model_name", "reasoning_executions", ["model_name"], unique=False)
    if not index_exists("reasoning_executions", "ix_reasoning_executions_tool_name"):
        op.create_index("ix_reasoning_executions_tool_name", "reasoning_executions", ["tool_name"], unique=False)
    if not index_exists("reasoning_executions", "idx_execution_user_started"):
        op.create_index("idx_execution_user_started", "reasoning_executions", ["user_id", "started_at"], unique=False)

    if op.get_bind().dialect.name != "sqlite":
        op.create_foreign_key(
            "fk_reasoning_executions_user_id_users",
            "reasoning_executions",
            "users",
            ["user_id"],
            ["id"],
        )


def downgrade() -> None:
    """Downgrade schema."""
    if op.get_bind().dialect.name != "sqlite":
        op.drop_constraint("fk_reasoning_executions_user_id_users", "reasoning_executions", type_="foreignkey")

    op.drop_index("idx_execution_user_started", table_name="reasoning_executions")
    op.drop_index("ix_reasoning_executions_tool_name", table_name="reasoning_executions")
    op.drop_index("ix_reasoning_executions_model_name", table_name="reasoning_executions")
    op.drop_index("ix_reasoning_executions_user_id", table_name="reasoning_executions")

    op.drop_column("reasoning_executions", "tool_name")
    op.drop_column("reasoning_executions", "model_name")
    op.drop_column("reasoning_executions", "user_id")
