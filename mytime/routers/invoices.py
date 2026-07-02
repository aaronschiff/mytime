from datetime import date
from decimal import Decimal, InvalidOperation

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


def _next_invoice_number(session) -> str:
    existing = list(session.scalars(
        select(Invoice.invoice_number).where(Invoice.invoice_number.is_not(None))
    ))
    max_num = 0
    for n in existing:
        try:
            max_num = max(max_num, int(n))
        except (ValueError, TypeError):
            pass
    return str(max_num + 1)


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


def _hourly_context(session, project, cutoff_date, **extra):
    rows = invoicing.build_invoice_preview(session, project.id, cutoff_date)
    summary = budget.project_summary(session, project)
    ctx = {
        "project": project,
        "rows": rows,
        "cutoff": cutoff_date.isoformat(),
        "currency": _currency(session),
        "total_tracked_seconds": sum(r.tracked_seconds for r in rows),
        "already_invoiced": summary.invoiced_value,
        "budget_remaining": summary.budget_remaining,
        "next_invoice_number": _next_invoice_number(session),
    }
    ctx.update(extra)
    return ctx


def _fixed_context(session, project, **extra):
    summary = budget.project_summary(session, project)
    ctx = {
        "project": project,
        "currency": _currency(session),
        "invoice_date": today().isoformat(),
        "already_invoiced": summary.invoiced_value,
        "tracked_value": summary.tracked_value,
        "budget_remaining": summary.budget_remaining,
        "next_invoice_number": _next_invoice_number(session),
    }
    ctx.update(extra)
    return ctx


def _number_taken(session, invoice_number: str) -> bool:
    return session.scalars(
        select(Invoice).where(Invoice.invoice_number == invoice_number)
    ).first() is not None


@router.get("/projects/{project_id}/invoices/new", response_class=HTMLResponse)
def build_page(project_id: int, request: Request, cutoff: str = "",
               session: Session = Depends(get_session)):
    project = projects.get_project(session, project_id)
    if project.status == "archived":
        return RedirectResponse(f"/projects/{project_id}", status_code=303)
    if project.billing_type == "fixed":
        return templates.TemplateResponse(request, "invoice_build.html",
                                          _fixed_context(session, project))
    cutoff_date = date.fromisoformat(cutoff) if cutoff else today()
    return templates.TemplateResponse(request, "invoice_build.html",
                                      _hourly_context(session, project, cutoff_date))


@router.post("/projects/{project_id}/invoices/new")
async def create(project_id: int, request: Request, session: Session = Depends(get_session)):
    project = projects.get_project(session, project_id)
    if project.status == "archived":
        return RedirectResponse(f"/projects/{project_id}", status_code=303)
    form = await request.form()
    invoice_number = (form.get("invoice_number") or "").strip() or None

    if project.billing_type == "fixed":
        amount_raw = (form.get("amount") or "").strip()
        label = (form.get("label") or "").strip() or None
        invoice_date = date.fromisoformat(form["invoice_date"]) if form.get("invoice_date") else today()
        try:
            amount = Decimal(amount_raw)
            if amount <= 0:
                raise ValueError
        except (InvalidOperation, ValueError):
            return templates.TemplateResponse(request, "invoice_build.html", _fixed_context(
                session, project, next_invoice_number=invoice_number or "",
                amount=amount_raw, label=label or "", invoice_date=invoice_date.isoformat(),
                error="Enter a valid invoice amount greater than zero.",
            ), status_code=400)
        if invoice_number and _number_taken(session, invoice_number):
            return templates.TemplateResponse(request, "invoice_build.html", _fixed_context(
                session, project, next_invoice_number=invoice_number,
                amount=amount_raw, label=label or "", invoice_date=invoice_date.isoformat(),
                error=f"Invoice number '{invoice_number}' already exists. Please use a different number.",
            ), status_code=400)
        inv = invoicing.create_fixed_invoice(
            session, project_id, amount, now(),
            invoice_number=invoice_number, label=label, invoice_date=invoice_date,
        )
        return RedirectResponse(f"/invoices/{inv.id}", status_code=303)

    cutoff_date = date.fromisoformat(form["cutoff"])
    task_ids = [int(v) for v in form.getlist("task_id")]
    seconds_by_task = {}
    for tid in task_ids:
        raw = str(form.get(f"duration_{tid}", "00:00"))
        seconds = parse_duration(raw)
        if seconds is None:
            return templates.TemplateResponse(request, "invoice_build.html", _hourly_context(
                session, project, cutoff_date, next_invoice_number=invoice_number or "",
                error=f"Couldn't read the duration {raw!r}. "
                      "Use hh:mm (minutes 00–59) or a whole number of hours.",
            ), status_code=400)
        seconds_by_task[tid] = seconds
    if invoice_number and _number_taken(session, invoice_number):
        return templates.TemplateResponse(request, "invoice_build.html", _hourly_context(
            session, project, cutoff_date, next_invoice_number=invoice_number,
            error=f"Invoice number '{invoice_number}' already exists. Please use a different number.",
        ), status_code=400)
    inv = invoicing.create_invoice(
        session, project_id, cutoff_date, seconds_by_task, now(), invoice_number=invoice_number
    )
    return RedirectResponse(f"/invoices/{inv.id}", status_code=303)


@router.get("/invoices/{invoice_id}", response_class=HTMLResponse)
def view(invoice_id: int, request: Request, session: Session = Depends(get_session)):
    invoice = invoicing.get_invoice(session, invoice_id)
    project = projects.get_project(session, invoice.project_id)
    return templates.TemplateResponse(request, "invoice_view.html", {
        "invoice": invoice,
        "project": project,
        "lines": invoicing.invoice_lines(session, invoice_id),
        "task_names": {t.id: t.name for t in task_types.list_task_types(session, include_inactive=True)},
        "currency": _currency(session),
    })


@router.post("/invoices/{invoice_id}/void")
def void(invoice_id: int, session: Session = Depends(get_session)):
    invoice = invoicing.get_invoice(session, invoice_id)
    project = projects.get_project(session, invoice.project_id)
    if project.status == "archived":
        return RedirectResponse(f"/invoices/{invoice_id}", status_code=303)
    pid = invoice.project_id
    invoicing.void_invoice(session, invoice_id)
    return RedirectResponse(f"/projects/{pid}", status_code=303)
