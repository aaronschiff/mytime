from datetime import timedelta

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from mytime.clock import now, today
from mytime.db import get_session
from mytime.services import timers, projects, task_types, time_entries as te

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
