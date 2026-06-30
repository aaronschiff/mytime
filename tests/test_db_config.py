"""SQLite connection hardening: every connection must wait on locks instead of
failing immediately, and the database must use WAL journalling for safe
concurrent reads/writes."""
from sqlalchemy import create_engine, text

from mytime import db


def test_configure_engine_sets_busy_timeout_and_wal(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'cfg.db'}")
    db.configure_engine(engine)
    with engine.connect() as conn:
        assert conn.execute(text("PRAGMA busy_timeout")).scalar() == 5000
        assert conn.execute(text("PRAGMA journal_mode")).scalar().lower() == "wal"


def test_busy_timeout_applies_to_every_new_connection(tmp_path):
    """busy_timeout is per-connection, so it must be reapplied on each connect,
    not just the first."""
    engine = create_engine(f"sqlite:///{tmp_path / 'cfg.db'}")
    db.configure_engine(engine)
    for _ in range(3):
        with engine.connect() as conn:
            assert conn.execute(text("PRAGMA busy_timeout")).scalar() == 5000
