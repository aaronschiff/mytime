import os
from collections.abc import Iterator

from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from mytime.models import Base, Client, Project


def configure_engine(engine) -> None:
    """Harden SQLite connections for safe concurrent single-writer access.

    - busy_timeout: wait (up to 5s) for a lock instead of failing immediately
      with "database is locked" — applied per connection, so it must run on
      every connect, not just the first.
    - WAL journalling: lets readers proceed during a write and is more
      crash-resilient than the default rollback journal. WAL is persisted in the
      database header, so setting it repeatedly is a harmless no-op. (Safe now
      that backups use the SQLite online-backup API rather than a file copy.)
    - foreign_keys: OFF by default in SQLite, and (like busy_timeout) scoped
      to the connection rather than persisted — must be set on every connect.
      Every delete path that could orphan a FK has been audited and fixed
      (see BACKLOG / docs/superpowers/plans/2026-07-02-fk-enforcement.md);
      this is the enforcement layer plus a safety net for anything future
      code forgets to guard.
    """
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_conn, _conn_record):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA busy_timeout=5000")
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()


DB_URL = os.environ.get("MYTIME_DB_URL", "sqlite:///mytime.db")
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
configure_engine(engine)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

_MIGRATIONS = [
    "ALTER TABLE settings ADD COLUMN invoice_prefix VARCHAR(20) DEFAULT 'INV-'",
    "ALTER TABLE invoice ADD COLUMN invoice_number VARCHAR(50)",
    "ALTER TABLE project ADD COLUMN client_id INTEGER REFERENCES client(id)",
    "ALTER TABLE settings ADD COLUMN default_gst_rate NUMERIC(5,2)",
    "ALTER TABLE project ADD COLUMN gst_enabled BOOLEAN NOT NULL DEFAULT 0",
    "ALTER TABLE project ADD COLUMN gst_rate NUMERIC(5,2)",
    "ALTER TABLE invoice ADD COLUMN gst_amount NUMERIC(12,2)",
    "ALTER TABLE project ADD COLUMN billing_type VARCHAR(20) NOT NULL DEFAULT 'hourly'",
    "ALTER TABLE invoice ADD COLUMN label VARCHAR(200)",
]


def _repair_client_ids(session) -> None:
    """Link every project to a valid Client row.

    Handles two cases: client_id is NULL (pre-Client-feature data), and
    client_id points at a client row that no longer exists (an orphan from
    a delete path that didn't check for linked projects — see BACKLOG).
    Both are repaired by looking up or creating a Client matching the
    project's client_name text field, which is always kept in sync.
    """
    from sqlalchemy import select
    valid_ids = set(session.scalars(select(Client.id)).all())
    all_projects = session.scalars(select(Project)).all()
    for project in all_projects:
        if project.client_id in valid_ids:
            continue
        if not project.client_name:
            continue
        client = session.scalars(
            select(Client).where(Client.name == project.client_name)
        ).first()
        if client is None:
            client = Client(name=project.client_name)
            session.add(client)
            session.flush()
            valid_ids.add(client.id)
        project.client_id = client.id
    session.commit()


def _apply_migration(conn, stmt: str) -> None:
    """Run one ALTER TABLE migration idempotently.

    Migrations are all column adds, so a "duplicate column name" error means the
    migration is already applied — the only error we should swallow. Anything
    else (missing table, locked or full disk, malformed SQL) is a real problem
    and must surface rather than be silently ignored.
    """
    try:
        conn.execute(text(stmt))
        conn.commit()
    except OperationalError as exc:
        conn.rollback()
        if "duplicate column name" not in str(exc.orig).lower():
            raise


def init_db() -> None:
    Base.metadata.create_all(engine)
    with engine.connect() as conn:
        for stmt in _MIGRATIONS:
            _apply_migration(conn, stmt)
    with SessionLocal() as session:
        _repair_client_ids(session)


def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
