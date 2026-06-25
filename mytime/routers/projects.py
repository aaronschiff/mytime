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


@router.get("/projects", response_class=HTMLResponse)
def list_page(request: Request, status: str = "active", session: Session = Depends(get_session)):
    return templates.TemplateResponse(request, "projects.html", {
        "projects": projects.list_projects(session, status=status),
        "currency": _currency(session),
    })


@router.get("/projects/new", response_class=HTMLResponse)
def new_page(request: Request, session: Session = Depends(get_session)):
    return templates.TemplateResponse(request, "project_form.html", {
        "project": None,
        "default_rate": settings_service.get_settings(session).default_hourly_rate,
    })


@router.post("/projects/new")
def create(
    client_name: str = Form(...), name: str = Form(...),
    hourly_rate: Decimal = Form(...), budget: str = Form(""), description: str = Form(""),
    session: Session = Depends(get_session),
):
    p = projects.create_project(session, client_name, name, hourly_rate, budget, description)
    return RedirectResponse(f"/projects/{p.id}", status_code=303)


@router.get("/projects/{project_id}/edit", response_class=HTMLResponse)
def edit_page(project_id: int, request: Request, session: Session = Depends(get_session)):
    return templates.TemplateResponse(request, "project_form.html", {
        "project": projects.get_project(session, project_id),
        "default_rate": settings_service.get_settings(session).default_hourly_rate,
    })


@router.post("/projects/{project_id}/edit")
def update(
    project_id: int,
    client_name: str = Form(...), name: str = Form(...),
    hourly_rate: Decimal = Form(...), budget: str = Form(""), description: str = Form(""),
    session: Session = Depends(get_session),
):
    projects.update_project(session, project_id, client_name, name, hourly_rate, budget, description)
    return RedirectResponse(f"/projects/{project_id}", status_code=303)


@router.get("/projects/{project_id}", response_class=HTMLResponse)
def detail_page(project_id: int, request: Request, session: Session = Depends(get_session)):
    return templates.TemplateResponse(request, "project_detail.html", {
        "project": projects.get_project(session, project_id),
        "currency": _currency(session),
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
        }, status_code=409)
    return RedirectResponse("/projects", status_code=303)
