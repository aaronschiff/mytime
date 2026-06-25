from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from mytime.clock import now, today
from mytime.db import get_session
from mytime.format import parse_hm
from mytime.services import invoicing, projects, settings_service, task_types
from mytime.templating import templates

router = APIRouter()


def _currency(session):
    return settings_service.get_settings(session).currency_symbol


@router.get("/projects/{project_id}/invoices/new", response_class=HTMLResponse)
def build_page(project_id: int, request: Request, cutoff: str = "", session: Session = Depends(get_session)):
    cutoff_date = date.fromisoformat(cutoff) if cutoff else today()
    return templates.TemplateResponse(request, "invoice_build.html", {
        "project": projects.get_project(session, project_id),
        "rows": invoicing.build_invoice_preview(session, project_id, cutoff_date),
        "cutoff": cutoff_date.isoformat(), "currency": _currency(session),
    })


@router.post("/projects/{project_id}/invoices/new")
async def create(project_id: int, request: Request, session: Session = Depends(get_session)):
    form = await request.form()
    cutoff_date = date.fromisoformat(form["cutoff"])
    task_ids = [int(v) for v in form.getlist("task_id")]
    seconds_by_task = {
        tid: parse_hm(int(form.get(f"hours_{tid}", 0)), int(form.get(f"minutes_{tid}", 0)))
        for tid in task_ids
    }
    invoice = invoicing.create_invoice(session, project_id, cutoff_date, seconds_by_task, now())
    return RedirectResponse(f"/invoices/{invoice.id}", status_code=303)


@router.get("/invoices/{invoice_id}", response_class=HTMLResponse)
def view(invoice_id: int, request: Request, session: Session = Depends(get_session)):
    invoice = invoicing.get_invoice(session, invoice_id)
    return templates.TemplateResponse(request, "invoice_view.html", {
        "invoice": invoice,
        "project": projects.get_project(session, invoice.project_id),
        "lines": invoicing.invoice_lines(session, invoice_id),
        "task_names": {t.id: t.name for t in task_types.list_task_types(session, include_inactive=True)},
        "currency": _currency(session),
    })


@router.post("/invoices/{invoice_id}/void")
def void(invoice_id: int, session: Session = Depends(get_session)):
    invoice = invoicing.get_invoice(session, invoice_id)
    pid = invoice.project_id
    invoicing.void_invoice(session, invoice_id)
    return RedirectResponse(f"/projects/{pid}", status_code=303)
