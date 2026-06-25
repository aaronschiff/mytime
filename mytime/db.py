import os
from collections.abc import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from mytime.models import Base, Client, Project

DB_URL = os.environ.get("MYTIME_DB_URL", "sqlite:///mytime.db")
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

_MIGRATIONS = [
    "ALTER TABLE settings ADD COLUMN invoice_prefix VARCHAR(20) DEFAULT 'INV-'",
    "ALTER TABLE invoice ADD COLUMN invoice_number VARCHAR(50)",
    "ALTER TABLE project ADD COLUMN client_id INTEGER REFERENCES client(id)",
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
