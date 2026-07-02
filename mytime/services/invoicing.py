from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import select
from sqlalchemy.orm import Session

from mytime.models import Invoice, InvoiceLine, Project, TaskType, TimeEntry


def _q(value: Decimal) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _amount(seconds: int, rate: Decimal) -> Decimal:
    return _q(Decimal(seconds) / Decimal(3600) * rate)


@dataclass
class InvoicePreviewRow:
    task_type_id: int
    task_name: str
    tracked_seconds: int


def _includable(project_id: int, cutoff_date: date):
    return (
        select(TimeEntry)
        .where(
            TimeEntry.project_id == project_id,
            TimeEntry.invoice_id.is_(None),
            TimeEntry.running_since.is_(None),
            TimeEntry.entry_date <= cutoff_date,
        )
    )


def build_invoice_preview(session: Session, project_id: int, cutoff_date: date) -> list[InvoicePreviewRow]:
    entries = list(session.scalars(_includable(project_id, cutoff_date)))
    totals: dict[int, int] = {}
    for e in entries:
        totals[e.task_type_id] = totals.get(e.task_type_id, 0) + e.seconds
    names = {t.id: t.name for t in session.scalars(select(TaskType))}
    rows = [InvoicePreviewRow(tid, names[tid], secs) for tid, secs in totals.items()]
    rows.sort(key=lambda r: r.task_name)
    return rows


def create_invoice(
    session, project_id, cutoff_date, invoiced_seconds_by_task, at: datetime,
    invoice_number: str | None = None,
) -> Invoice:
    project = session.get(Project, project_id)
    rate = project.hourly_rate
    entries = list(session.scalars(_includable(project_id, cutoff_date)))

    tracked: dict[int, int] = {}
    for e in entries:
        tracked[e.task_type_id] = tracked.get(e.task_type_id, 0) + e.seconds

    invoice = Invoice(project_id=project_id, cutoff_date=cutoff_date,
                      rate_snapshot=rate, total_amount=Decimal("0.00"),
                      invoice_number=invoice_number)
    session.add(invoice)
    session.flush()

    total = Decimal("0.00")
    for tid, tracked_secs in tracked.items():
        inv_secs = int(invoiced_seconds_by_task.get(tid, tracked_secs))
        amount = _amount(inv_secs, rate)
        total += amount
        session.add(InvoiceLine(invoice_id=invoice.id, task_type_id=tid,
                                tracked_seconds=tracked_secs, invoiced_seconds=inv_secs, amount=amount))
    for e in entries:
        e.invoice_id = invoice.id
    invoice.total_amount = _q(total)
    if project.gst_enabled and project.gst_rate:
        invoice.gst_amount = _q(total * project.gst_rate / Decimal("100"))
    session.commit()
    return invoice


def create_fixed_invoice(
    session, project_id, amount, at: datetime,
    invoice_number: str | None = None, label: str | None = None,
    invoice_date: date | None = None,
) -> Invoice:
    """Create a flat-amount invoice for a fixed-fee project.

    The amount is entered directly and unrelated to tracked time, so no
    ``InvoiceLine`` rows are created and no ``TimeEntry`` is touched. ``cutoff_date``
    and ``rate_snapshot`` are NOT NULL on the model, so we store harmless values
    (the invoice date and the project's rate) rather than widen the schema.
    """
    project = session.get(Project, project_id)
    total = _q(amount)
    invoice = Invoice(
        project_id=project_id,
        cutoff_date=invoice_date or at.date(),
        rate_snapshot=project.hourly_rate,
        total_amount=total,
        invoice_number=invoice_number,
        label=label,
    )
    if project.gst_enabled and project.gst_rate:
        invoice.gst_amount = _q(total * project.gst_rate / Decimal("100"))
    session.add(invoice)
    session.commit()
    return invoice


def void_invoice(session: Session, invoice_id: int) -> None:
    for e in session.scalars(select(TimeEntry).where(TimeEntry.invoice_id == invoice_id)):
        e.invoice_id = None
    session.query(InvoiceLine).filter(InvoiceLine.invoice_id == invoice_id).delete()
    session.delete(session.get(Invoice, invoice_id))
    session.commit()


def list_invoices(session: Session, project_id: int) -> list[Invoice]:
    return list(session.scalars(
        select(Invoice).where(Invoice.project_id == project_id).order_by(Invoice.created_at.desc(), Invoice.id.desc())
    ))


def get_invoice(session: Session, invoice_id: int) -> Invoice:
    return session.get(Invoice, invoice_id)


def invoice_lines(session: Session, invoice_id: int) -> list[InvoiceLine]:
    return list(session.scalars(select(InvoiceLine).where(InvoiceLine.invoice_id == invoice_id)))
