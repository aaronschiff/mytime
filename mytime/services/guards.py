from sqlalchemy import select
from sqlalchemy.orm import Session

from mytime.models import Invoice, Project, TimeEntry


class ProjectHasInvoicesError(Exception):
    pass


class EntryLockedError(Exception):
    pass


class ClientHasTimeError(Exception):
    pass


def project_has_invoices(session: Session, project_id: int) -> bool:
    return session.scalars(
        select(Invoice.id).where(Invoice.project_id == project_id).limit(1)
    ).first() is not None


def delete_project(session: Session, project_id: int) -> None:
    if project_has_invoices(session, project_id):
        raise ProjectHasInvoicesError(project_id)
    session.query(TimeEntry).filter(TimeEntry.project_id == project_id).delete()
    session.delete(session.get(Project, project_id))
    session.commit()


def can_delete_client(session: Session, client_id: int) -> bool:
    """Return False if any project linked to this client has any time entries."""
    project_ids = session.scalars(
        select(Project.id).where(Project.client_id == client_id)
    ).all()
    if not project_ids:
        return True
    has_time = session.scalars(
        select(TimeEntry.id).where(TimeEntry.project_id.in_(project_ids)).limit(1)
    ).first()
    return has_time is None


def ensure_unlocked(entry: TimeEntry) -> None:
    if entry.invoice_id is not None:
        raise EntryLockedError(entry.id)
