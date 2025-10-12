"""Phase 7 schema updates for engine pipelines, profiles, and endpoint sinks."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20251110_phase7_engine_pipelines_profiles"
down_revision = "20251101_add_agent_actions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "engine_module_profiles",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("config", sa.JSON, nullable=False, server_default=sa.text("'{}'")),
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
    op.create_index(
        "ix_profiles_kind_name",
        "engine_module_profiles",
        ["kind", "name"],
    )

    op.create_table(
        "pipeline_steps",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "pipeline_id",
            sa.Integer,
            sa.ForeignKey("pipelines.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("step_order", sa.Integer, nullable=False),
        sa.Column(
            "module_profile_id",
            sa.Integer,
            sa.ForeignKey("engine_module_profiles.id", ondelete="RESTRICT"),
            nullable=False,
        ),
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
    op.create_index(
        "ix_pipeline_steps_order",
        "pipeline_steps",
        ["pipeline_id", "step_order"],
    )
    op.create_index(
        "ix_pipeline_steps_pipeline",
        "pipeline_steps",
        ["pipeline_id"],
    )

    op.add_column(
        "pipelines",
        sa.Column("scope", sa.String(length=16), nullable=False, server_default="engine"),
    )
    op.add_column(
        "pipelines",
        sa.Column(
            "endpoint_id",
            sa.Integer,
            sa.ForeignKey("engine_endpoints.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    op.add_column(
        "engine_endpoints",
        sa.Column("sink_kind", sa.String(length=16), nullable=False, server_default="folder"),
    )
    op.add_column(
        "engine_endpoints",
        sa.Column(
            "sink_config",
            sa.JSON,
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )

    op.create_table(
        "engine_endpoint_messages",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "endpoint_id",
            sa.Integer,
            sa.ForeignKey("engine_endpoints.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "received_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("raw", sa.LargeBinary, nullable=True),
        sa.Column("processed", sa.LargeBinary, nullable=True),
        sa.Column("meta", sa.JSON, nullable=True),
    )
    op.create_index(
        "ix_engine_endpoint_messages_endpoint",
        "engine_endpoint_messages",
        ["endpoint_id", "received_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_engine_endpoint_messages_endpoint",
        table_name="engine_endpoint_messages",
    )
    op.drop_table("engine_endpoint_messages")
    op.drop_column("engine_endpoints", "sink_config")
    op.drop_column("engine_endpoints", "sink_kind")
    op.drop_column("pipelines", "endpoint_id")
    op.drop_column("pipelines", "scope")
    op.drop_index(
        "ix_pipeline_steps_order",
        table_name="pipeline_steps",
    )
    op.drop_index(
        "ix_pipeline_steps_pipeline",
        table_name="pipeline_steps",
    )
    op.drop_table("pipeline_steps")
    op.drop_index(
        "ix_profiles_kind_name",
        table_name="engine_module_profiles",
    )
    op.drop_table("engine_module_profiles")
