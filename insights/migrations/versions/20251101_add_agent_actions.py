"""Add agent_actions table for Activity Timeline."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20251101_add_agent_actions"
down_revision = "20251016_add_engine_endpoints"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_actions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("ts", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("actor", sa.String(length=64), nullable=False, server_default="demo-agent"),
        sa.Column("intent", sa.String(length=64), nullable=False),
        sa.Column("params", sa.JSON, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="planned"),
        sa.Column("result", sa.JSON, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("endpoint_id", sa.Integer, nullable=True),
        sa.Column("job_id", sa.Integer, nullable=True),
        sa.Column("run_id", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_agent_actions_ts", "agent_actions", ["ts"])
    op.create_index("ix_agent_actions_intent", "agent_actions", ["intent"])
    op.create_index("ix_agent_actions_status", "agent_actions", ["status"])


def downgrade() -> None:
    op.drop_index("ix_agent_actions_status", table_name="agent_actions")
    op.drop_index("ix_agent_actions_intent", table_name="agent_actions")
    op.drop_index("ix_agent_actions_ts", table_name="agent_actions")
    op.drop_table("agent_actions")
