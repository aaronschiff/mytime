from datetime import date
from sqlalchemy import select
from sqlalchemy.orm import Session

from mytime.models import TimeEntry
from mytime.services import guards


def list_entries(session, project_id=None, date_from=None, date_to=None) -> list[TimeEntry]:
    stmt = select(TimeEntry)
    if project_id is not None:
        stmt = stmt.where(TimeEntry.project_id == project_id)
    if date_from is not None:
        stmt = stmt.where(TimeEntry.entry_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(TimeEntry.entry_date <= date_to)
    stmt = stmt.order_by(TimeEntry.entry_date.desc(), TimeEntry.id.desc())
    return list(session.scalars(stmt))


def get_entry(session: Session, entry_id: int) -> TimeEntry:
    return session.get(TimeEntry, entry_id)


def create_entry(session, project_id, task_type_id, entry_date, seconds, notes) -> TimeEntry:
    e = TimeEntry(
        project_id=project_id, task_type_id=task_type_id,
        entry_date=entry_date, seconds=int(seconds), notes=(notes or None),
    )
    session.add(e)
    session.commit()
    return e


def update_entry(session, entry_id, task_type_id, entry_date, seconds, notes) -> TimeEntry:
    e = get_entry(session, entry_id)
    guards.ensure_unlocked(e)
    e.task_type_id = task_type_id
    e.entry_date = entry_date
    e.seconds = int(seconds)
    e.notes = notes or None
    session.commit()
    return e


def delete_entry(session, entry_id) -> None:
    e = get_entry(session, entry_id)
    guards.ensure_unlocked(e)
    session.delete(e)
    session.commit()
