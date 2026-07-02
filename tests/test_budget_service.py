from decimal import Decimal
from datetime import date
from mytime.models import Invoice, TimeEntry, TaskType
from mytime.services import budget, projects


def _entry(session, pid, secs, invoiced_id=None):
    t = session.query(TaskType).first()
    if t is None:
        t = TaskType(name="A"); session.add(t); session.flush()
    e = TimeEntry(project_id=pid, task_type_id=t.id, entry_date=date(2026, 6, 25),
                  seconds=secs, invoice_id=invoiced_id)
    session.add(e); session.commit(); return e


def test_summary_no_budget(session):
    p = projects.create_project(session, "C", "A", Decimal("100"), None, None)
    _entry(session, p.id, 3600)            # 1h uninvoiced @ 100 = 100
    s = budget.project_summary(session, p)
    assert s.uninvoiced_value == Decimal("100.00")
    assert s.budget_remaining is None
    assert s.over_budget is False
    assert s.total_tracked_seconds == 3600


def test_summary_with_invoice_and_remaining(session):
    p = projects.create_project(session, "C", "A", Decimal("100"), Decimal("500"), None)
    session.add(Invoice(project_id=p.id, cutoff_date=date(2026, 6, 25),
                        rate_snapshot=Decimal("100"), total_amount=Decimal("200")))
    session.commit()
    _entry(session, p.id, 3600)            # uninvoiced 1h @100 = 100
    s = budget.project_summary(session, p)
    assert s.invoiced_value == Decimal("200.00")
    assert s.uninvoiced_value == Decimal("100.00")
    assert s.budget_remaining == Decimal("200.00")   # 500 - 300
    assert s.over_budget is False


def test_summary_over_budget(session):
    p = projects.create_project(session, "C", "A", Decimal("100"), Decimal("50"), None)
    _entry(session, p.id, 3600)            # 100 uninvoiced > 50 budget
    s = budget.project_summary(session, p)
    assert s.over_budget is True
    assert s.exceedance == Decimal("50.00")
    assert s.budget_remaining == Decimal("-50.00")


def test_fixed_summary_tracks_time_value_not_invoiced(session):
    p = projects.create_project(session, "C", "Fixed", Decimal("200"), Decimal("45000"),
                                None, billing_type="fixed")
    # Invoiced amount is decoupled and must NOT drive budget progress
    session.add(Invoice(project_id=p.id, cutoff_date=date(2026, 6, 25),
                        rate_snapshot=Decimal("200"), total_amount=Decimal("15000")))
    session.commit()
    _entry(session, p.id, 3600 * 10)       # 10h @ 200 = 2000 tracked value
    s = budget.project_summary(session, p)
    assert s.invoiced_value == Decimal("15000.00")
    assert s.tracked_value == Decimal("2000.00")
    assert s.budget_remaining == Decimal("43000.00")   # 45000 - 2000 (not - invoiced)
    assert s.over_budget is False


def test_fixed_summary_over_fee_when_tracked_value_exceeds_budget(session):
    p = projects.create_project(session, "C", "Fixed", Decimal("200"), Decimal("1000"),
                                None, billing_type="fixed")
    _entry(session, p.id, 3600 * 6)        # 6h @ 200 = 1200 > 1000 fee
    s = budget.project_summary(session, p)
    assert s.tracked_value == Decimal("1200.00")
    assert s.over_budget is True
    assert s.exceedance == Decimal("200.00")
    assert s.budget_remaining == Decimal("-200.00")
