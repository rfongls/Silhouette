from __future__ import annotations

import os

from alembic import command
from alembic.config import Config

from engine.contracts import Issue, Message, Result
from insights.store import InsightsStore, reset_store


def test_insights_migration_apply(tmp_path):
    db_url = f"sqlite:///{(tmp_path / 'migration.db')}"
    previous = os.environ.get("INSIGHTS_DB_URL")
    os.environ["INSIGHTS_DB_URL"] = db_url
    cfg = Config("insights/migrations/alembic.ini")
    cfg.set_main_option("script_location", "insights/migrations")
    cfg.set_main_option("sqlalchemy.url", db_url)
    try:
        command.upgrade(cfg, "head")
    finally:
        if previous is None:
            os.environ.pop("INSIGHTS_DB_URL", None)
        else:
            os.environ["INSIGHTS_DB_URL"] = previous

    reset_store()
    store = InsightsStore.from_env(url=db_url)
    run = store.start_run("migration-test")
    store.record_result(
        run_id=run.id,
        result=Result(
            message=Message(id="m-1", raw=b"demo"),
            issues=[Issue(severity="passed", code="structure")],
        ),
    )
    summary = store.summaries()
    assert summary["totals"]["runs"] == 1
    assert summary["totals"]["messages"] == 1
    assert summary["by_run"][0]["issues"]["passed"] == 1
