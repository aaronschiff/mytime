from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from mytime.db import get_session
from mytime.services import clients as clients_service, projects, settings_service
from mytime.services.guards import ClientHasTimeError
from mytime.templating import templates

router = APIRouter()


def _currency(session):
    return settings_service.get_settings(session).currency_symbol


@router.get("/clients", response_class=HTMLResponse)
def list_page(request: Request, session: Session = Depends(get_session)):
    all_clients = clients_service.list_clients(session)
    all_projects = projects.list_projects(session)
    project_counts = {}
    for p in all_projects:
        if p.client_id is not None:
            project_counts[p.client_id] = project_counts.get(p.client_id, 0) + 1
    return templates.TemplateResponse(request, "clients.html", {
        "clients": all_clients,
        "project_counts": project_counts,
    })


@router.get("/clients/{client_id}", response_class=HTMLResponse)
def detail_page(client_id: int, request: Request, session: Session = Depends(get_session)):
    from sqlalchemy import select
    from mytime.models import Project
    client = clients_service.get_client(session, client_id)
    client_projects = list(session.scalars(
        select(Project)
        .where(Project.client_id == client_id)
        .order_by(Project.name)
    ))
    return templates.TemplateResponse(request, "client_detail.html", {
        "client": client,
        "projects": client_projects,
        "currency": _currency(session),
    })


@router.get("/clients/{client_id}/edit", response_class=HTMLResponse)
def edit_page(client_id: int, request: Request, session: Session = Depends(get_session)):
    client = clients_service.get_client(session, client_id)
    return templates.TemplateResponse(request, "client_form.html", {
        "client": client,
    })


@router.post("/clients/{client_id}/edit")
def update(
    client_id: int,
    name: str = Form(...),
    session: Session = Depends(get_session),
):
    clients_service.update_client(session, client_id, name)
    return RedirectResponse(f"/clients/{client_id}", status_code=303)


@router.post("/clients/{client_id}/delete")
def delete(client_id: int, request: Request, session: Session = Depends(get_session)):
    try:
        clients_service.delete_client(session, client_id)
    except ClientHasTimeError:
        all_clients = clients_service.list_clients(session)
        all_projects = projects.list_projects(session)
        project_counts = {}
        for p in all_projects:
            if p.client_id is not None:
                project_counts[p.client_id] = project_counts.get(p.client_id, 0) + 1
        return templates.TemplateResponse(request, "clients.html", {
            "clients": all_clients,
            "project_counts": project_counts,
            "error": "Cannot delete client: they have projects with tracked time.",
        }, status_code=409)
    return RedirectResponse("/clients", status_code=303)
