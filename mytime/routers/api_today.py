from datetime import timedelta

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from mytime.clock import now, today
from mytime.db import get_session
from mytime.format import parse_duration
from mytime.services import timers, projects, task_types, time_entries as te
from mytime.services.guards import EntryLockedError

router = APIRouter()

_DURATION_ERROR = "Invalid time format. Use hh:mm (e.g. 2:30) or a whole number of hours (e.g. 2)."


def _error(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": message})


def _today_state(session: Session) -> dict:
    day = today()
    at = now()
    active_projects = projects.list_projects(session, status="active")
    active_task_types = task_types.list_task_types(session)
    project_names = {p.id: p.name for p in projects.list_projects(session)}
    task_names = {t.id: t.name for t in task_types.list_task_types(session, include_inactive=True)}

    entries = []
    total = 0
    for e in timers.todays_timers(session, day):
        elapsed = timers.live_elapsed(e, at)
        total += elapsed
        entries.append({
            "id": e.id,
            "project_id": e.project_id,
            "project_name": project_names.get(e.project_id, ""),
            "task_type_id": e.task_type_id,
            "task_type_name": task_names.get(e.task_type_id, ""),
            "notes": e.notes or "",
            "base_seconds": e.seconds,
            "running": e.running_since is not None,
            "since": e.running_since.isoformat() + "Z" if e.running_since else None,
            "locked": e.invoice_id is not None,
        })

    week_seconds = sum(
        timers.live_elapsed(e, at)
        for e in te.list_entries(session, date_from=day - timedelta(days=6), date_to=day)
    )

    return {
        "day": day.isoformat(),
        "total_seconds": total,
        "week_seconds": week_seconds,
        "projects": [{"id": p.id, "name": p.name} for p in active_projects],
        "task_types": [{"id": t.id, "name": t.name} for t in active_task_types],
        "entries": entries,
    }


@router.get("/api/today")
def get_today(session: Session = Depends(get_session)):
    return _today_state(session)


class CreateEntryBody(BaseModel):
    project_id: int
    task_type_id: int
    notes: str = ""
    start: bool = True
    duration: str = "00:00"


@router.post("/api/today/entries")
def create_entry(body: CreateEntryBody, session: Session = Depends(get_session)):
    if body.start:
        timers.add_timer(session, body.project_id, body.task_type_id, body.notes, now())
    else:
        seconds = parse_duration(body.duration)
        if seconds is None:
            return _error(400, _DURATION_ERROR)
        te.create_entry(session, body.project_id, body.task_type_id, today(), seconds, body.notes)
    return _today_state(session)


@router.post("/api/today/{entry_id}/start")
def start_entry(entry_id: int, session: Session = Depends(get_session)):
    if te.get_entry(session, entry_id) is None:
        return _error(404, "Time entry not found.")
    try:
        timers.start_timer(session, entry_id, now())
    except EntryLockedError:
        return _error(403, "This time entry is locked to an invoice.")
    return _today_state(session)


@router.post("/api/today/{entry_id}/stop")
def stop_entry(entry_id: int, session: Session = Depends(get_session)):
    if te.get_entry(session, entry_id) is None:
        return _error(404, "Time entry not found.")
    try:
        timers.stop_timer(session, entry_id, now())
    except EntryLockedError:
        return _error(403, "This time entry is locked to an invoice.")
    return _today_state(session)


class SetTimeBody(BaseModel):
    time_hm: str


@router.post("/api/today/{entry_id}/set-time")
def set_time_entry(entry_id: int, body: SetTimeBody, session: Session = Depends(get_session)):
    entry = te.get_entry(session, entry_id)
    if entry is None:
        return _error(404, "Time entry not found.")
    if entry.invoice_id is not None:
        return _error(403, "This time entry is locked to an invoice.")
    if entry.running_since is not None:
        return _error(403, "Stop the timer before editing elapsed time.")
    seconds = parse_duration(body.time_hm)
    if seconds is None:
        return _error(400, _DURATION_ERROR)
    entry.seconds = seconds
    session.commit()
    return _today_state(session)


class EditEntryBody(BaseModel):
    project_id: int
    task_type_id: int
    duration: str
    notes: str = ""


@router.post("/api/today/{entry_id}/edit")
def edit_entry(entry_id: int, body: EditEntryBody, session: Session = Depends(get_session)):
    entry = te.get_entry(session, entry_id)
    if entry is None:
        return _error(404, "Time entry not found.")
    project = projects.get_project(session, entry.project_id)
    if project.status != "active":
        return _error(403, "Time entries for archived projects cannot be edited.")
    seconds = parse_duration(body.duration)
    if seconds is None:
        return _error(400, _DURATION_ERROR)
    try:
        if entry.running_since is not None:
            timers.stop_timer(session, entry_id, now())
        te.update_entry(session, entry_id, body.project_id, body.task_type_id,
                        entry.entry_date, seconds, body.notes)
    except EntryLockedError:
        return _error(403, "This time entry is locked to an invoice.")
    return _today_state(session)


@router.delete("/api/today/{entry_id}")
def delete_entry(entry_id: int, session: Session = Depends(get_session)):
    if te.get_entry(session, entry_id) is None:
        return _error(404, "Time entry not found.")
    try:
        te.delete_entry(session, entry_id)
    except EntryLockedError:
        return _error(403, "This time entry is locked to an invoice.")
    return _today_state(session)
