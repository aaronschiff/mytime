from datetime import datetime, date
from sqlalchemy import select
from sqlalchemy.orm import Session

from mytime.clock import today
from mytime.models import TimeEntry
from mytime.services import guards


def live_elapsed(entry: TimeEntry, at: datetime) -> int:
    if entry.running_since is None:
        return entry.seconds
    return entry.seconds + int((at - entry.running_since).total_seconds())


def running_timer(session: Session) -> TimeEntry | None:
    return session.scalars(
        select(TimeEntry).where(TimeEntry.running_since.is_not(None)).limit(1)
    ).first()


def stop_all_running(session: Session, at: datetime) -> None:
    for e in session.scalars(select(TimeEntry).where(TimeEntry.running_since.is_not(None))):
        e.seconds = live_elapsed(e, at)
        e.running_since = None
    session.commit()


def start_timer(session: Session, entry_id: int, at: datetime) -> TimeEntry:
    e = session.get(TimeEntry, entry_id)
    guards.ensure_unlocked(e)
    stop_all_running(session, at)
    e.running_since = at
    if e.first_started_at is None:
        e.first_started_at = at
    session.commit()
    return e


def stop_timer(session: Session, entry_id: int, at: datetime) -> TimeEntry:
    e = session.get(TimeEntry, entry_id)
    if e.running_since is not None:
        e.seconds = live_elapsed(e, at)
        e.running_since = None
        session.commit()
    return e


def add_timer(session: Session, project_id: int, task_type_id: int, notes, at: datetime) -> TimeEntry:
    e = TimeEntry(
        project_id=project_id, task_type_id=task_type_id, notes=(notes or None),
        entry_date=at.date(), seconds=0,
    )
    session.add(e)
    session.commit()
    return start_timer(session, e.id, at)


def todays_timers(session: Session, day: date) -> list[TimeEntry]:
    stmt = select(TimeEntry).where(
        (TimeEntry.entry_date == day) | (TimeEntry.running_since.is_not(None))
    )
    rows = list(session.scalars(stmt))
    rows.sort(key=lambda e: (e.first_started_at is not None, e.first_started_at or datetime.min, e.id), reverse=True)
    return rows
