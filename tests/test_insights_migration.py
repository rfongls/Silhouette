from __future__ import annotations

from alembic import command
from alembic.config import Config

from engine.contracts import Issue, Message, Result
from insights.store import InsightsStore, reset_store


def test_insights_migration_apply(tmp_path):
    db_url = f"sqlite:///{(tmp_path / 'migration.db')}"
    cfg = Config("insights/migrations/alembic.ini")
    cfg.set_main_option("script_location", "insights/migrations")
    cfg.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(cfg, "head")

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
