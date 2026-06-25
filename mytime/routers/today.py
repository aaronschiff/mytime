from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from mytime.clock import now, today
from mytime.db import get_session
from mytime.services import timers, projects, task_types
from mytime.templating import templates

router = APIRouter()


def _context(session: Session) -> dict:
    day = today()
    at = now()
    ps = projects.list_projects(session, status="active")
    ts = task_types.list_task_types(session)
    rows = []
    total = 0
    for e in timers.todays_timers(session, day):
        elapsed = timers.live_elapsed(e, at)
        total += elapsed
        rows.append({
            "entry": e,
            "running": e.running_since is not None,
            "elapsed": elapsed,                 # live value at render, for first paint
            "base": e.seconds,                  # stored accumulated seconds (no running delta)
            "since_iso": e.running_since.isoformat() if e.running_since else "",
        })
    return {
        "day": day.isoformat(), "rows": rows, "total_seconds": total,
        "all_projects": ps, "task_types": ts,
        "names": {p.id: f"{p.client_name} — {p.name}" for p in projects.list_projects(session)},
        "task_names": {t.id: t.name for t in task_types.list_task_types(session, include_inactive=True)},
    }


@router.get("/today", response_class=HTMLResponse)
def today_page(request: Request, session: Session = Depends(get_session)):
    return templates.TemplateResponse(request, "today.html", _context(session))


def _body(request: Request, session: Session) -> HTMLResponse:
    return templates.TemplateResponse(request, "_today_body.html", _context(session))


@router.post("/today/add")
def add(project_id: int = Form(...), task_type_id: int = Form(...),
        notes: str = Form(""), session: Session = Depends(get_session)):
    timers.add_timer(session, project_id, task_type_id, notes, now())
    return RedirectResponse("/today", status_code=303)


@router.post("/today/{entry_id}/start", response_class=HTMLResponse)
def start(entry_id: int, request: Request, session: Session = Depends(get_session)):
    timers.start_timer(session, entry_id, now())
    return _body(request, session)


@router.post("/today/{entry_id}/stop", response_class=HTMLResponse)
def stop(entry_id: int, request: Request, session: Session = Depends(get_session)):
    timers.stop_timer(session, entry_id, now())
    return _body(request, session)


@router.post("/today/{entry_id}/delete", response_class=HTMLResponse)
def delete(entry_id: int, request: Request, session: Session = Depends(get_session)):
    from mytime.services import time_entries as te
    te.delete_entry(session, entry_id)
    return _body(request, session)
