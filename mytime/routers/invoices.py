from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from mytime.clock import now, today
from mytime.db import get_session
from mytime.format import parse_duration
from mytime.models import Invoice
from mytime.services import invoicing, projects, settings_service, task_types, budget
from mytime.templating import templates

router = APIRouter()


def _currency(session):
    return settings_service.get_settings(session).currency_symbol


@router.get("/invoices", response_class=HTMLResponse)
def invoice_list(request: Request, session: Session = Depends(get_session)):
    all_invoices = list(session.scalars(
        select(Invoice).order_by(Invoice.created_at.desc(), Invoice.id.desc())
    ))
    all_projects = {p.id: p for p in projects.list_projects(session)}
    return templates.TemplateResponse(request, "invoice_list.html", {
        "invoices": all_invoices,
        "all_projects": all_projects,
        "currency": _currency(session),
    })


@router.get("/projects/{project_id}/invoices/new", response_class=HTMLResponse)
def build_page(project_id: int, request: Request, cutoff: str = "", session: Session = Depends(get_session)):
    cutoff_date = date.fromisoformat(cutoff) if cutoff else today()
    project = projects.get_project(session, project_id)
    rows = invoicing.build_invoice_preview(session, project_id, cutoff_date)
    total_tracked = sum(r.tracked_seconds for r in rows)
    summary = budget.project_summary(session, project)
    settings = settings_service.get_settings(session)
    # Check uniqueness hint - get existing invoice numbers
    existing_numbers = list(session.scalars(
        select(Invoice.invoice_number).where(Invoice.invoice_number.is_not(None))
    ))
    return templates.TemplateResponse(request, "invoice_build.html", {
        "project": project,
        "rows": rows,
        "cutoff": cutoff_date.isoformat(),
        "currency": _currency(session),
        "total_tracked_seconds": total_tracked,
        "already_invoiced": summary.invoiced_value,
        "budget_remaining": summary.budget_remaining,
        "invoice_number_prefix": settings.invoice_prefix or "",
        "existing_numbers": existing_numbers,
    })


@router.post("/projects/{project_id}/invoices/new")
async def create(project_id: int, request: Request, session: Session = Depends(get_session)):
    form = await request.form()
    cutoff_date = date.fromisoformat(form["cutoff"])
    invoice_number = (form.get("invoice_number") or "").strip() or None
    task_ids = [int(v) for v in form.getlist("task_id")]
    seconds_by_task = {
        tid: parse_duration(str(form.get(f"duration_{tid}", "00:00")))
        for tid in task_ids
    }
    # Check uniqueness of invoice_number
    if invoice_number:
        existing = session.scalars(
            select(Invoice).where(Invoice.invoice_number == invoice_number)
        ).first()
        if existing:
            project = projects.get_project(session, project_id)
            rows = invoicing.build_invoice_preview(session, project_id, cutoff_date)
            total_tracked = sum(r.tracked_seconds for r in rows)
            summary = budget.project_summary(session, project)
            settings = settings_service.get_settings(session)
            existing_numbers = list(session.scalars(
                select(Invoice.invoice_number).where(Invoice.invoice_number.is_not(None))
            ))
            return templates.TemplateResponse(request, "invoice_build.html", {
                "project": project,
                "rows": rows,
                "cutoff": cutoff_date.isoformat(),
                "currency": _currency(session),
                "total_tracked_seconds": total_tracked,
                "already_invoiced": summary.invoiced_value,
                "budget_remaining": summary.budget_remaining,
                "invoice_number_prefix": invoice_number,
                "existing_numbers": existing_numbers,
                "error": f"Invoice number '{invoice_number}' already exists. Please use a different number.",
            }, status_code=400)
    invoice = invoicing.create_invoice(
        session, project_id, cutoff_date, seconds_by_task, now(), invoice_number=invoice_number
    )
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

