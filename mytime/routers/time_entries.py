from datetime import date

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from mytime.clock import now, today
from mytime.db import get_session
from mytime.format import parse_duration
from mytime.services import time_entries as te, projects, task_types, timers
from mytime.services.guards import EntryLockedError
from mytime.templating import templates

router = APIRouter()

_DURATION_ERROR = "Invalid time format. Use hh:mm (e.g. 2:30) or a whole number of hours (e.g. 2)."


def _lookup(session):
    ps = projects.list_projects(session)
    ts = task_types.list_task_types(session, include_inactive=True)
    return ps, ts, {p.id: f"{p.client_name} — {p.name}" for p in ps}, {t.id: t.name for t in ts}


@router.get("/time", response_class=HTMLResponse)
def time_page(request: Request, project_id: str = "", session: Session = Depends(get_session)):
    pid = int(project_id) if project_id else None
    ps, ts, names, task_names = _lookup(session)
    project_statuses = {p.id: p.status for p in ps}
    return templates.TemplateResponse(request, "time.html", {
        "entries": te.list_entries(session, project_id=pid),
        "all_projects": ps, "names": names, "task_names": task_names,
        "filter_project_id": pid,
        "project_statuses": project_statuses,
    })


@router.get("/time/new", response_class=HTMLResponse)
def new_page(request: Request, from_page: str = "", project_id: str = "",
             session: Session = Depends(get_session)):
    preset_project_id = int(project_id) if project_id else None
    ps, ts, _, _ = _lookup(session)
    return templates.TemplateResponse(request, "time_entry_form.html", {
        "entry": None, "all_projects": ps, "task_types": ts, "today": today().isoformat(),
        "from_page": from_page or "/time",
        "preset_project_id": preset_project_id,
    })


@router.post("/time/new")
def create(
    request: Request,
    project_id: int = Form(...), task_type_id: int = Form(...),
    entry_date: date = Form(...), duration: str = Form("00:00"),
    notes: str = Form(""), from_page: str = Form(""),
    session: Session = Depends(get_session),
):
    seconds = parse_duration(duration)
    if seconds is None:
        ps, ts, _, _ = _lookup(session)
        return templates.TemplateResponse(request, "time_entry_form.html", {
            "entry": None, "all_projects": ps, "task_types": ts, "today": today().isoformat(),
            "from_page": from_page or "/time",
            "error": _DURATION_ERROR,
            "preset_project_id": project_id,
        }, status_code=400)
    te.create_entry(session, project_id, task_type_id, entry_date, seconds, notes)
    return RedirectResponse(from_page or "/time", status_code=303)


@router.get("/time/{entry_id}/edit", response_class=HTMLResponse)
def edit_page(entry_id: int, request: Request, from_page: str = "",
              session: Session = Depends(get_session)):
    entry = te.get_entry(session, entry_id)
    if entry.invoice_id is not None:
        return Response("This time entry is locked to an invoice and cannot be edited.", status_code=403)
    project = projects.get_project(session, entry.project_id)
    if project.status != "active":
        return Response("Time entries for archived projects cannot be edited.", status_code=403)
    if entry.running_since is not None:
        timers.stop_timer(session, entry_id, now())
        entry = te.get_entry(session, entry_id)
    ps, ts, _, _ = _lookup(session)
    return templates.TemplateResponse(request, "time_entry_form.html", {
        "entry": entry, "all_projects": ps, "task_types": ts,
        "today": today().isoformat(),
        "from_page": from_page or "/time",
    })


@router.post("/time/{entry_id}/edit")
def update(
    entry_id: int, request: Request,
    project_id: int = Form(...), task_type_id: int = Form(...),
    entry_date: date = Form(...), duration: str = Form("00:00"),
    notes: str = Form(""), from_page: str = Form(""),
    session: Session = Depends(get_session),
):
    seconds = parse_duration(duration)
    if seconds is None:
        entry = te.get_entry(session, entry_id)
        ps, ts, _, _ = _lookup(session)
        return templates.TemplateResponse(request, "time_entry_form.html", {
            "entry": entry, "all_projects": ps, "task_types": ts,
            "today": today().isoformat(),
            "from_page": from_page or "/time",
            "error": _DURATION_ERROR,
        }, status_code=400)
    try:
        te.update_entry(session, entry_id, project_id, task_type_id, entry_date, seconds, notes)
    except EntryLockedError:
        return Response("This time entry is locked to an invoice and cannot be edited.", status_code=403)
    return RedirectResponse(from_page or "/time", status_code=303)


@router.post("/time/{entry_id}/delete")
def delete(entry_id: int, session: Session = Depends(get_session)):
    te.delete_entry(session, entry_id)
    return RedirectResponse("/time", status_code=303)
