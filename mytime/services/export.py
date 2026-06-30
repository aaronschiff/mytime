from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import select
from sqlalchemy.orm import Session

from mytime import clock, format
from mytime.models import Invoice, Project, TaskType
from mytime.services import time_entries, timers

CSV_COLUMNS = [
    "entry_id", "date", "created_at", "client", "project", "task_type", "notes",
    "hourly_rate", "hours", "amount", "invoice_number",
    "running", "project_status",
]


def _q(value) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def time_entries_csv_rows(session: Session, at: datetime | None = None) -> list[dict]:
    at = at or clock.now()
    entries = time_entries.list_entries(session)
    entries.sort(key=lambda e: (e.entry_date, e.created_at, e.id))

    projects = {p.id: p for p in session.scalars(select(Project))}
    task_names = {t.id: t.name for t in session.scalars(select(TaskType))}
    invoice_numbers = {i.id: (i.invoice_number or "") for i in session.scalars(select(Invoice))}

    rows = []
    for e in entries:
        project = projects[e.project_id]
        hours = _q(Decimal(timers.live_elapsed(e, at)) / Decimal(3600))
        rows.append({
            "entry_id": e.id,
            "date": e.entry_date.isoformat(),
            "created_at": format.fmt_datetime(clock.to_local(e.created_at)),
            "client": project.client_name,
            "project": project.name,
            "task_type": task_names[e.task_type_id],
            "notes": e.notes or "",
            "hourly_rate": _q(project.hourly_rate),
            "hours": hours,
            "amount": _q(hours * project.hourly_rate),
            "invoice_number": invoice_numbers.get(e.invoice_id, "") if e.invoice_id is not None else "",
            "running": "Yes" if e.running_since is not None else "No",
            "project_status": project.status,
        })
    return rows
