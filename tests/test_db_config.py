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


def test_configure_engine_sets_foreign_keys_on(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'cfg.db'}")
    db.configure_engine(engine)
    with engine.connect() as conn:
        assert conn.execute(text("PRAGMA foreign_keys")).scalar() == 1


def test_foreign_keys_applies_to_every_new_connection(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'cfg.db'}")
    db.configure_engine(engine)
    for _ in range(3):
        with engine.connect() as conn:
            assert conn.execute(text("PRAGMA foreign_keys")).scalar() == 1


def test_foreign_keys_block_orphaning_delete(tmp_path):
    """With enforcement on, deleting a client that a project still references
    must raise at the DB layer even if application code forgot to guard it —
    this is the safety net behind the can_delete_client check."""
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy.orm import sessionmaker
    from mytime.models import Base, Client, Project
    from decimal import Decimal

    engine = create_engine(f"sqlite:///{tmp_path / 'fk.db'}")
    db.configure_engine(engine)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as session:
        client = Client(name="Acme")
        session.add(client)
        session.flush()
        session.add(Project(
            client_name="Acme", name="Website", hourly_rate=Decimal("1"),
            status="active", billing_type="hourly", client_id=client.id,
        ))
        session.commit()

        session.delete(client)
        with pytest.raises(IntegrityError):
            session.commit()


def test_repair_client_ids_fixes_orphaned_reference(tmp_path):
    """A project whose client_id points at a client row that no longer exists
    (e.g. from before this fix shipped) must be repaired by re-linking to a
    client with the matching client_name, not left dangling."""
    from sqlalchemy.orm import sessionmaker
    from mytime.models import Base, Client, Project

    engine = create_engine(f"sqlite:///{tmp_path / 'orphan.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as session:
        project = Project(
            client_name="Acme", name="Website", hourly_rate=1,
            status="active", billing_type="hourly",
        )
        session.add(project)
        session.commit()
        # Simulate a pre-existing orphan: client_id pointing at a row that
        # doesn't exist (this can't be produced via the ORM anymore now that
        # can_delete_client blocks it — it models data from before that fix).
        session.execute(text("UPDATE project SET client_id = 999 WHERE id = :id"), {"id": project.id})
        session.commit()

        db._repair_client_ids(session)

        project = session.execute(text("SELECT client_id FROM project WHERE name='Website'")).scalar()
        client = session.execute(text("SELECT id, name FROM client WHERE name='Acme'")).first()
        assert client is not None
        assert project == client.id
