from datetime import date

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from mytime.clock import today
from mytime.db import get_session
from mytime.format import parse_hm
from mytime.services import time_entries as te, projects, task_types
from mytime.templating import templates

router = APIRouter()


def _lookup(session):
    ps = projects.list_projects(session)
    ts = task_types.list_task_types(session, include_inactive=True)
    return ps, ts, {p.id: f"{p.client_name} — {p.name}" for p in ps}, {t.id: t.name for t in ts}


@router.get("/time", response_class=HTMLResponse)
def time_page(request: Request, project_id: str = "", session: Session = Depends(get_session)):
    pid = int(project_id) if project_id else None
    ps, ts, names, task_names = _lookup(session)
    return templates.TemplateResponse(request, "time.html", {
        "entries": te.list_entries(session, project_id=pid),
        "all_projects": ps, "names": names, "task_names": task_names,
        "filter_project_id": pid,
    })


@router.get("/time/new", response_class=HTMLResponse)
def new_page(request: Request, session: Session = Depends(get_session)):
    ps, ts, _, _ = _lookup(session)
    return templates.TemplateResponse(request, "time_entry_form.html", {
        "entry": None, "all_projects": ps, "task_types": ts, "today": today().isoformat(),
    })


@router.post("/time/new")
def create(
    project_id: int = Form(...), task_type_id: int = Form(...),
    entry_date: date = Form(...), hours: int = Form(0), minutes: int = Form(0),
    notes: str = Form(""), session: Session = Depends(get_session),
):
    te.create_entry(session, project_id, task_type_id, entry_date, parse_hm(hours, minutes), notes)
    return RedirectResponse("/time", status_code=303)


@router.get("/time/{entry_id}/edit", response_class=HTMLResponse)
def edit_page(entry_id: int, request: Request, session: Session = Depends(get_session)):
    ps, ts, _, _ = _lookup(session)
    return templates.TemplateResponse(request, "time_entry_form.html", {
        "entry": te.get_entry(session, entry_id), "all_projects": ps, "task_types": ts,
        "today": today().isoformat(),
    })


@router.post("/time/{entry_id}/edit")
def update(
    entry_id: int, task_type_id: int = Form(...), entry_date: date = Form(...),
    hours: int = Form(0), minutes: int = Form(0), notes: str = Form(""),
    session: Session = Depends(get_session),
):
    te.update_entry(session, entry_id, task_type_id, entry_date, parse_hm(hours, minutes), notes)
    return RedirectResponse("/time", status_code=303)


@router.post("/time/{entry_id}/delete")
def delete(entry_id: int, session: Session = Depends(get_session)):
    te.delete_entry(session, entry_id)
    return RedirectResponse("/time", status_code=303)
