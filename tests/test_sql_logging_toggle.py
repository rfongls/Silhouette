from pathlib import Path

from sqlalchemy import create_engine, text

from api.debug_log import set_debug_enabled
from api.sql_logging import install_sql_logging


def test_sql_logging_toggle_first_statement_logged(tmp_path: Path) -> None:
    log_path = tmp_path / "server_sql.log"
    engine = create_engine("sqlite:///:memory:", future=True)
    install_sql_logging(engine, log_path=log_path)

    set_debug_enabled(False)
    with engine.begin() as connection:
        connection.execute(text("select 1"))
    assert log_path.read_text(encoding="utf-8").strip() == ""

    set_debug_enabled(True)
    with engine.begin() as connection:
        connection.execute(text("select 2"))
    content = log_path.read_text(encoding="utf-8")
    assert "SQL begin id=" in content
    assert "SQL end   id=" in content
