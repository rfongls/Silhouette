"""Add engine_endpoints table."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20251016_add_engine_endpoints"
down_revision = "20251015_add_engine_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "engine_endpoints",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False, unique=True),
        sa.Column(
            "pipeline_id",
            sa.Integer,
            sa.ForeignKey("pipelines.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("config", sa.JSON, nullable=False),
        sa.Column(
            "status", sa.String(length=16), nullable=False, server_default="stopped"
        ),
        sa.Column("last_error", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_engine_endpoints_kind", "engine_endpoints", ["kind"])


def downgrade() -> None:
    op.drop_index("ix_engine_endpoints_kind", table_name="engine_endpoints")
    op.drop_table("engine_endpoints")
