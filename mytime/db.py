import os
from collections.abc import Iterator

from sqlalchemy import create_engine, event, text
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
    """
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_conn, _conn_record):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA busy_timeout=5000")
        cur.execute("PRAGMA journal_mode=WAL")
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
]


def _populate_client_ids(session) -> None:
    """Populate client_id on projects that don't have one yet."""
    from sqlalchemy import select
    projects = session.scalars(
        select(Project).where(Project.client_id.is_(None))
    ).all()
    for project in projects:
        if not project.client_name:
            continue
        client = session.scalars(
            select(Client).where(Client.name == project.client_name)
        ).first()
        if client is None:
            client = Client(name=project.client_name)
            session.add(client)
            session.flush()
        project.client_id = client.id
    session.commit()


def init_db() -> None:
    Base.metadata.create_all(engine)
    with engine.connect() as conn:
        for stmt in _MIGRATIONS:
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception:
                pass
    with SessionLocal() as session:
        _populate_client_ids(session)


def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
