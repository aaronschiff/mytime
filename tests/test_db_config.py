"""SQLite connection hardening: every connection must wait on locks instead of
failing immediately, and the database must use WAL journalling for safe
concurrent reads/writes."""
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

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


def test_apply_migration_is_idempotent_for_duplicate_column(tmp_path):
    """Re-running a column-add migration is the normal idempotent case and must
    be swallowed silently."""
    engine = create_engine(f"sqlite:///{tmp_path / 'm.db'}")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE t (id INTEGER PRIMARY KEY, x INTEGER)"))
    with engine.connect() as conn:
        db._apply_migration(conn, "ALTER TABLE t ADD COLUMN x INTEGER")  # no raise


def test_apply_migration_reraises_real_errors(tmp_path):
    """A migration that fails for any reason other than 'already applied' (e.g.
    a missing table, a locked or full disk) must surface, not be swallowed."""
    engine = create_engine(f"sqlite:///{tmp_path / 'm.db'}")
    with engine.connect() as conn:
        with pytest.raises(OperationalError):
            db._apply_migration(conn, "ALTER TABLE does_not_exist ADD COLUMN y INTEGER")
