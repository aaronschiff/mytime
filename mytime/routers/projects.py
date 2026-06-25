from decimal import Decimal

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from mytime.db import get_session
from mytime.services import projects, guards, settings_service, budget
from mytime.templating import templates

router = APIRouter()


def _currency(session):
    return settings_service.get_settings(session).currency_symbol


def _existing_clients(session):
    return sorted({p.client_name for p in projects.list_projects(session)})


@router.get("/projects", response_class=HTMLResponse)
def list_page(request: Request, status: str = "active", session: Session = Depends(get_session)):
    ps = projects.list_projects(session, status=status, order_by_date=True)
    summaries = {p.id: budget.project_summary(session, p) for p in ps}
    return templates.TemplateResponse(request, "projects.html", {
        "projects": ps,
        "summaries": summaries,
        "currency": _currency(session),
        "status": status,
    })


@router.get("/projects/new", response_class=HTMLResponse)
def new_page(request: Request, from_page: str = "", session: Session = Depends(get_session)):
    settings = settings_service.get_settings(session)
    return templates.TemplateResponse(request, "project_form.html", {
        "project": None,
        "default_rate": settings.default_hourly_rate,
        "default_gst_rate": float(settings.default_gst_rate) if settings.default_gst_rate is not None else None,
        "currency": _currency(session),
        "existing_clients": _existing_clients(session),
        "from_page": from_page or "/projects",
    })


@router.post("/projects/new")
def create(
    request: Request,
    client_name: str = Form(...), name: str = Form(...),
    hourly_rate: Decimal = Form(...), budget: str = Form(""), description: str = Form(""),
    gst_enabled: str = Form(""), gst_rate: str = Form(""),
    from_page: str = Form(""),
    session: Session = Depends(get_session),
):
    try:
        p = projects.create_project(
            session, client_name, name, hourly_rate, budget, description,
            gst_enabled=bool(gst_enabled),
            gst_rate=gst_rate if gst_enabled else None,
        )
    except ValueError as exc:
        settings = settings_service.get_settings(session)
        return templates.TemplateResponse(request, "project_form.html", {
            "project": None,
            "default_rate": settings.default_hourly_rate,
            "default_gst_rate": float(settings.default_gst_rate) if settings.default_gst_rate is not None else None,
            "currency": _currency(session),
            "existing_clients": _existing_clients(session),
            "from_page": from_page or "/projects",
            "error": str(exc),
        }, status_code=422)
    return RedirectResponse(f"/projects/{p.id}", status_code=303)


@router.get("/projects/{project_id}/edit", response_class=HTMLResponse)
def edit_page(project_id: int, request: Request, from_page: str = "",
              session: Session = Depends(get_session)):
    settings = settings_service.get_settings(session)
    return templates.TemplateResponse(request, "project_form.html", {
        "project": projects.get_project(session, project_id),
        "default_rate": settings.default_hourly_rate,
        "default_gst_rate": float(settings.default_gst_rate) if settings.default_gst_rate is not None else None,
        "currency": _currency(session),
        "existing_clients": _existing_clients(session),
        "from_page": from_page or f"/projects/{project_id}",
    })


@router.post("/projects/{project_id}/edit")
def update(
    project_id: int,
    request: Request,
    client_name: str = Form(...), name: str = Form(...),
    hourly_rate: Decimal = Form(...), budget: str = Form(""), description: str = Form(""),
    gst_enabled: str = Form(""), gst_rate: str = Form(""),
    from_page: str = Form(""),
    session: Session = Depends(get_session),
):
    try:
        projects.update_project(
            session, project_id, client_name, name, hourly_rate, budget, description,
            gst_enabled=bool(gst_enabled),
            gst_rate=gst_rate if gst_enabled else None,
        )
    except ValueError as exc:
        settings = settings_service.get_settings(session)
        return templates.TemplateResponse(request, "project_form.html", {
            "project": projects.get_project(session, project_id),
            "default_rate": settings.default_hourly_rate,
            "default_gst_rate": float(settings.default_gst_rate) if settings.default_gst_rate is not None else None,
            "currency": _currency(session),
            "existing_clients": _existing_clients(session),
            "from_page": from_page or f"/projects/{project_id}",
            "error": str(exc),
        }, status_code=422)
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
def set_status(project_id: int, status: str = Form(...), from_page: str = Form(""),
               session: Session = Depends(get_session)):
    projects.set_status(session, project_id, status)
    return RedirectResponse(from_page or "/projects", status_code=303)


@router.post("/projects/{project_id}/delete")
def delete(project_id: int, request: Request, session: Session = Depends(get_session)):
    try:
        guards.delete_project(session, project_id)
    except guards.ProjectHasInvoicesError:
        ps = projects.list_projects(session, status="active")
        return templates.TemplateResponse(request, "projects.html", {
            "projects": ps,
            "summaries": {p.id: budget.project_summary(session, p) for p in ps},
            "currency": _currency(session),
            "status": "active",
        }, status_code=409)
    return RedirectResponse("/projects", status_code=303)
