from decimal import Decimal

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from mytime.db import get_session
from mytime.services import projects, guards, settings_service
from mytime.templating import templates

router = APIRouter()


def _currency(session):
    return settings_service.get_settings(session).currency_symbol


def _existing_clients(session):
    return sorted({p.client_name for p in projects.list_projects(session)})


@router.get("/projects", response_class=HTMLResponse)
def list_page(request: Request, status: str = "active", session: Session = Depends(get_session)):
    return templates.TemplateResponse(request, "projects.html", {
        "projects": projects.list_projects(session, status=status),
        "currency": _currency(session),
        "status": status,
    })


@router.get("/projects/new", response_class=HTMLResponse)
def new_page(request: Request, from_page: str = "", session: Session = Depends(get_session)):
    return templates.TemplateResponse(request, "project_form.html", {
        "project": None,
        "default_rate": settings_service.get_settings(session).default_hourly_rate,
        "currency": _currency(session),
        "existing_clients": _existing_clients(session),
        "from_page": from_page or "/projects",
    })


@router.post("/projects/new")
def create(
    client_name: str = Form(...), name: str = Form(...),
    hourly_rate: Decimal = Form(...), budget: str = Form(""), description: str = Form(""),
    from_page: str = Form(""),
    session: Session = Depends(get_session),
):
    p = projects.create_project(session, client_name, name, hourly_rate, budget, description)
    return RedirectResponse(f"/projects/{p.id}", status_code=303)


@router.get("/projects/{project_id}/edit", response_class=HTMLResponse)
def edit_page(project_id: int, request: Request, from_page: str = "", session: Session = Depends(get_session)):
    return templates.TemplateResponse(request, "project_form.html", {
        "project": projects.get_project(session, project_id),
        "default_rate": settings_service.get_settings(session).default_hourly_rate,
        "currency": _currency(session),
        "existing_clients": _existing_clients(session),
        "from_page": from_page or f"/projects/{project_id}",
    })


@router.post("/projects/{project_id}/edit")
def update(
    project_id: int,
    client_name: str = Form(...), name: str = Form(...),
    hourly_rate: Decimal = Form(...), budget: str = Form(""), description: str = Form(""),
    from_page: str = Form(""),
    session: Session = Depends(get_session),
):
    projects.update_project(session, project_id, client_name, name, hourly_rate, budget, description)
    return RedirectResponse(from_page or f"/projects/{project_id}", status_code=303)


@router.get("/projects/{project_id}", response_class=HTMLResponse)
def detail_page(project_id: int, request: Request, session: Session = Depends(get_session)):
    from mytime.services import time_entries as te, task_types, budget, invoicing
    project = projects.get_project(session, project_id)
    summary = budget.project_summary(session, project)
    task_names = {t.id: t.name for t in task_types.list_task_types(session, include_inactive=True)}
    return templates.TemplateResponse(request, "project_detail.html", {
        "project": project, "currency": _currency(session),
        "entries": te.list_entries(session, project_id=project_id),
        "task_names": task_names, "summary": summary, "s": summary,
        "invoices": invoicing.list_invoices(session, project_id),
    })


@router.post("/projects/{project_id}/status")
def set_status(project_id: int, status: str = Form(...), session: Session = Depends(get_session)):
    projects.set_status(session, project_id, status)
    return RedirectResponse("/projects", status_code=303)


@router.post("/projects/{project_id}/delete")
def delete(project_id: int, request: Request, session: Session = Depends(get_session)):
    try:
        guards.delete_project(session, project_id)
    except guards.ProjectHasInvoicesError:
        return templates.TemplateResponse(request, "projects.html", {
            "projects": projects.list_projects(session, status="active"),
            "currency": _currency(session),
            "status": "active",
        }, status_code=409)
    return RedirectResponse("/projects", status_code=303)
