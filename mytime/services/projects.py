from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session

from mytime.models import Project


def list_projects(session: Session, status: str | None = None, order_by_date: bool = False) -> list[Project]:
    stmt = select(Project)
    if status is not None:
        stmt = stmt.where(Project.status == status)
    if order_by_date:
        stmt = stmt.order_by(Project.created_at.desc())
    else:
        stmt = stmt.order_by(Project.client_name, Project.name)
    return list(session.scalars(stmt))


def get_project(session: Session, project_id: int) -> Project:
    return session.get(Project, project_id)


def _check_duplicate(session: Session, client_name: str, name: str, exclude_id: int | None = None) -> None:
    stmt = select(Project).where(Project.client_name == client_name, Project.name == name)
    if exclude_id is not None:
        stmt = stmt.where(Project.id != exclude_id)
    if session.scalar(stmt):
        raise ValueError(f"A project named \"{name}\" already exists for client \"{client_name}\".")


def create_project(session, client_name, name, hourly_rate, budget, description,
                   gst_enabled: bool = False, gst_rate=None) -> Project:
    from mytime.services.clients import find_or_create as _find_or_create_client
    stripped = client_name.strip()
    _check_duplicate(session, stripped, name.strip())
    client = _find_or_create_client(session, stripped) if stripped else None
    p = Project(
        client_name=stripped,
        name=name.strip(),
        hourly_rate=Decimal(hourly_rate),
        budget=Decimal(budget) if budget not in (None, "") else None,
        description=(description or None),
        status="active",
        client_id=client.id if client is not None else None,
        gst_enabled=gst_enabled,
        gst_rate=Decimal(gst_rate) if gst_rate not in (None, "") else None,
    )
    session.add(p)
    session.commit()
    return p


def update_project(session, project_id, client_name, name, hourly_rate, budget, description,
                   gst_enabled: bool = False, gst_rate=None) -> Project:
    from mytime.services.clients import find_or_create as _find_or_create_client
    p = get_project(session, project_id)
    stripped = client_name.strip()
    _check_duplicate(session, stripped, name.strip(), exclude_id=project_id)
    client = _find_or_create_client(session, stripped) if stripped else None
    p.client_name = stripped
    p.name = name.strip()
    p.hourly_rate = Decimal(hourly_rate)
    p.budget = Decimal(budget) if budget not in (None, "") else None
    p.description = description or None
    p.client_id = client.id if client is not None else None
    p.gst_enabled = gst_enabled
    p.gst_rate = Decimal(gst_rate) if gst_rate not in (None, "") else None
    session.commit()
    return p


def set_status(session: Session, project_id: int, status: str) -> Project:
    p = get_project(session, project_id)
    p.status = status
    session.commit()
    return p
