from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from mytime.models import Invoice, Project, TimeEntry


def _q(value: Decimal) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass
class ProjectSummary:
    project: Project
    invoiced_value: Decimal
    uninvoiced_value: Decimal
    uninvoiced_seconds: int
    total_tracked_seconds: int
    budget_remaining: Decimal | None
    over_budget: bool
    exceedance: Decimal


def project_summary(session: Session, project: Project) -> ProjectSummary:
    invoiced = session.scalar(
        select(func.coalesce(func.sum(Invoice.total_amount), 0)).where(Invoice.project_id == project.id)
    )
    uninvoiced_secs = session.scalar(
        select(func.coalesce(func.sum(TimeEntry.seconds), 0))
        .where(TimeEntry.project_id == project.id, TimeEntry.invoice_id.is_(None))
    )
    total_secs = session.scalar(
        select(func.coalesce(func.sum(TimeEntry.seconds), 0)).where(TimeEntry.project_id == project.id)
    )
    invoiced_value = _q(invoiced)
    uninvoiced_value = _q(Decimal(uninvoiced_secs) / Decimal(3600) * project.hourly_rate)

    remaining = None
    over = False
    exceedance = Decimal("0.00")
    if project.budget is not None:
        remaining = _q(project.budget - invoiced_value - uninvoiced_value)
        if remaining < 0:
            over = True
            exceedance = _q(-remaining)
    return ProjectSummary(
        project=project, invoiced_value=invoiced_value, uninvoiced_value=uninvoiced_value,
        uninvoiced_seconds=int(uninvoiced_secs), total_tracked_seconds=int(total_secs),
        budget_remaining=remaining, over_budget=over, exceedance=exceedance,
    )
