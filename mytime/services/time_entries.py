from datetime import date, datetime
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from mytime import clock
from mytime.models import TimeEntry
from mytime.services import guards


def _entry_filter(stmt, project_id=None, date_from=None, date_to=None):
    if project_id is not None:
        stmt = stmt.where(TimeEntry.project_id == project_id)
    if date_from is not None:
        stmt = stmt.where(TimeEntry.entry_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(TimeEntry.entry_date <= date_to)
    return stmt


def count_entries(session, project_id=None, date_from=None, date_to=None) -> int:
    stmt = select(func.count()).select_from(TimeEntry)
    stmt = _entry_filter(stmt, project_id, date_from, date_to)
    return session.scalar(stmt)


def list_entries(session, project_id=None, date_from=None, date_to=None,
                 limit: int | None = None, offset: int = 0) -> list[TimeEntry]:
    stmt = select(TimeEntry)
    stmt = _entry_filter(stmt, project_id, date_from, date_to)
    stmt = stmt.order_by(TimeEntry.entry_date.desc(), TimeEntry.id.desc())
    if limit is not None:
        stmt = stmt.limit(limit).offset(offset)
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


def update_entry(session, entry_id, project_id, task_type_id, entry_date, seconds, notes,
                 at: datetime | None = None) -> TimeEntry:
    """seconds=None leaves the entry's time (and any live run) completely
    untouched. A running entry is never stopped by an edit: a submitted
    duration is "total elapsed as of now", so the run restarts at `at` —
    keeping the old running_since would double-count the current run."""
    e = get_entry(session, entry_id)
    guards.ensure_unlocked(e)
    e.project_id = project_id
    e.task_type_id = task_type_id
    e.entry_date = entry_date
    if seconds is not None:
        e.seconds = int(seconds)
        if e.running_since is not None:
            e.running_since = at if at is not None else clock.now()
    e.notes = notes or None
    session.commit()
    return e


def delete_entry(session, entry_id) -> None:
    e = get_entry(session, entry_id)
    guards.ensure_unlocked(e)
    session.delete(e)
    session.commit()
