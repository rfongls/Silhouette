from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20251112_failed_messages"
down_revision = "20251110_phase7_engine_pipelines_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "engine_failed_messages",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "endpoint_id",
            sa.Integer,
            sa.ForeignKey("engine_endpoints.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "pipeline_id",
            sa.Integer,
            sa.ForeignKey("pipelines.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "received_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("raw", sa.LargeBinary, nullable=False),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("meta", sa.JSON, nullable=True),
    )
    op.create_index(
        "ix_failed_endpoint_time",
        "engine_failed_messages",
        ["endpoint_id", "received_at"],
    )
    op.create_index(
        "ix_failed_pipeline_time",
        "engine_failed_messages",
        ["pipeline_id", "received_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_failed_pipeline_time", table_name="engine_failed_messages")
    op.drop_index("ix_failed_endpoint_time", table_name="engine_failed_messages")
    op.drop_table("engine_failed_messages")
