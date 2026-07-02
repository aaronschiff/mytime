from sqlalchemy import select
from sqlalchemy.orm import Session

from mytime.models import Invoice, Project, TimeEntry


class ProjectHasInvoicesError(Exception):
    pass


class EntryLockedError(Exception):
    pass


class ProjectHasTimeError(Exception):
    pass


class ClientHasProjectsError(Exception):
    pass


def project_has_invoices(session: Session, project_id: int) -> bool:
    return session.scalars(
        select(Invoice.id).where(Invoice.project_id == project_id).limit(1)
    ).first() is not None


def project_has_time(session: Session, project_id: int) -> bool:
    return session.scalars(
        select(TimeEntry.id).where(TimeEntry.project_id == project_id).limit(1)
    ).first() is not None


def delete_project(session: Session, project_id: int) -> None:
    # Refuse to delete any project that has tracked time. Invoiced time would
    # also have invoices (more specific message); uninvoiced time is potentially
    # unbilled money. Either way the project should be archived, not deleted.
    if project_has_invoices(session, project_id):
        raise ProjectHasInvoicesError(project_id)
    if project_has_time(session, project_id):
        raise ProjectHasTimeError(project_id)
    session.delete(session.get(Project, project_id))
    session.commit()


def can_delete_client(session: Session, client_id: int) -> bool:
    """Return False if the client has any linked project at all.

    A client can only be safely deleted once no project references it —
    even a project with zero tracked time still holds a client_id that
    would otherwise dangle once the client row is gone.
    """
    return session.scalars(
        select(Project.id).where(Project.client_id == client_id).limit(1)
    ).first() is None


def ensure_unlocked(entry: TimeEntry) -> None:
    if entry.invoice_id is not None:
        raise EntryLockedError(entry.id)
