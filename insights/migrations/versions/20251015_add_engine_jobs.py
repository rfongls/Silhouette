"""add engine jobs table

Revision ID: 20251015_add_engine_jobs
Revises: 20251012_add_pipelines_table
Create Date: 2025-10-15
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20251015_add_engine_jobs"
down_revision = "20251012_add_pipelines_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "engine_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "pipeline_id",
            sa.Integer(),
            sa.ForeignKey("pipelines.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default="queued",
        ),
        sa.Column(
            "priority",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "attempts",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "max_attempts",
            sa.Integer(),
            nullable=False,
            server_default="3",
        ),
        sa.Column(
            "scheduled_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("leased_by", sa.String(length=64), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(), nullable=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("engine_runs.id"), nullable=True),
        sa.Column("dedupe_key", sa.String(length=255), nullable=True, unique=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_engine_jobs_status_sched_prio",
        "engine_jobs",
        ["status", "scheduled_at", "priority"],
    )


def downgrade() -> None:
    op.drop_index("ix_engine_jobs_status_sched_prio", table_name="engine_jobs")
    op.drop_table("engine_jobs")
