from pathlib import Path

from sqlalchemy import create_engine, text

from api.debug_log import set_debug_enabled
from api.sql_logging import install_sql_logging


def test_sql_logging_writes_frames(tmp_path: Path):
    log_path = tmp_path / "server_sql.log"
    engine = create_engine("sqlite:///:memory:", future=True)
    install_sql_logging(engine, log_path=log_path)
    set_debug_enabled(True)
    with engine.begin() as connection:
        connection.execute(text("create table t (id integer primary key, v text)"))
        connection.execute(text("insert into t (v) values (:v)"), {"v": "secret"})
        connection.execute(text("select * from t where v = :v"), {"v": "secret"})
    content = log_path.read_text(encoding="utf-8")
    assert "SQL begin id=" in content
    assert "SQL end   id=" in content
    assert "***REDACTED***" in content or '"v": "***REDACTED***"' in content
