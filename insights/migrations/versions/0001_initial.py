"""Initial insights schema.

Revision ID: 0001_initial
Revises: None
Create Date: 2024-07-15
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "engine_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("pipeline_name", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "engine_messages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("engine_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("message_id", sa.String(length=255), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "engine_issues",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("message_id", sa.Integer(), sa.ForeignKey("engine_messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("code", sa.String(length=120), nullable=False),
        sa.Column("segment", sa.String(length=40), nullable=True),
        sa.Column("field", sa.String(length=40), nullable=True),
        sa.Column("component", sa.String(length=40), nullable=True),
        sa.Column("subcomponent", sa.String(length=40), nullable=True),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
    )
    op.create_index("ix_engine_issues_severity", "engine_issues", ["severity"])
    op.create_index("ix_engine_issues_code", "engine_issues", ["code"])


def downgrade() -> None:
    op.drop_index("ix_engine_issues_code", table_name="engine_issues")
    op.drop_index("ix_engine_issues_severity", table_name="engine_issues")
    op.drop_table("engine_issues")
    op.drop_table("engine_messages")
    op.drop_table("engine_runs")
