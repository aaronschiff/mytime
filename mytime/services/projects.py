from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session

from mytime.models import Project


def list_projects(session: Session, status: str | None = None) -> list[Project]:
    stmt = select(Project)
    if status is not None:
        stmt = stmt.where(Project.status == status)
    stmt = stmt.order_by(Project.client_name, Project.name)
    return list(session.scalars(stmt))


def get_project(session: Session, project_id: int) -> Project:
    return session.get(Project, project_id)


def create_project(session, client_name, name, hourly_rate, budget, description) -> Project:
    p = Project(
        client_name=client_name.strip(),
        name=name.strip(),
        hourly_rate=Decimal(hourly_rate),
        budget=Decimal(budget) if budget not in (None, "") else None,
        description=(description or None),
        status="active",
    )
    session.add(p)
    session.commit()
    return p


def update_project(session, project_id, client_name, name, hourly_rate, budget, description) -> Project:
    p = get_project(session, project_id)
    p.client_name = client_name.strip()
    p.name = name.strip()
    p.hourly_rate = Decimal(hourly_rate)
    p.budget = Decimal(budget) if budget not in (None, "") else None
    p.description = description or None
    session.commit()
    return p


def set_status(session: Session, project_id: int, status: str) -> Project:
    p = get_project(session, project_id)
    p.status = status
    session.commit()
    return p
