from pathlib import Path

from sqlalchemy import create_engine, text

from api.debug_log import set_debug_enabled
from api.sql_logging import install_sql_logging


def test_sql_logging_error_frame(tmp_path: Path):
    log_path = tmp_path / "server_sql.log"
    eng = create_engine("sqlite:///:memory:", future=True)
    install_sql_logging(eng, log_path=log_path)
    set_debug_enabled(True)

    try:
        with eng.begin() as cxn:
            cxn.execute(text("select * from non_existent where v = :v"), {"v": "secret"})
    except Exception:
        pass

    content = log_path.read_text(encoding="utf-8")
    assert "SQL begin id=" in content
    assert "SQL error id=" in content
    assert "***REDACTED***" in content
