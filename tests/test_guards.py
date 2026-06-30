import pytest
from decimal import Decimal
from datetime import date
from mytime.models import Invoice, TimeEntry, TaskType
from mytime.services import projects, guards


def _entry(session, project_id):
    tt = TaskType(name="Analysis"); session.add(tt); session.flush()
    e = TimeEntry(project_id=project_id, task_type_id=tt.id, entry_date=date(2026, 6, 25), seconds=600)
    session.add(e); session.commit()
    return e


def test_delete_project_with_uninvoiced_time_raises(session):
    """Uninvoiced time is potentially unbilled money — deletion must refuse and
    leave both the project and its entries intact."""
    p = projects.create_project(session, "C", "A", Decimal("1"), None, None)
    _entry(session, p.id)
    with pytest.raises(guards.ProjectHasTimeError):
        guards.delete_project(session, p.id)
    assert projects.get_project(session, p.id) is not None
    assert session.query(TimeEntry).count() == 1


def test_delete_empty_project_succeeds(session):
    """A project with no tracked time can still be deleted (e.g. created by mistake)."""
    p = projects.create_project(session, "C", "A", Decimal("1"), None, None)
    guards.delete_project(session, p.id)
    assert projects.get_project(session, p.id) is None


def test_delete_project_with_invoices_raises(session):
    p = projects.create_project(session, "C", "A", Decimal("1"), None, None)
    session.add(Invoice(project_id=p.id, cutoff_date=date(2026, 6, 25),
                        rate_snapshot=Decimal("1"), total_amount=Decimal("0")))
    session.commit()
    assert guards.project_has_invoices(session, p.id) is True
    with pytest.raises(guards.ProjectHasInvoicesError):
        guards.delete_project(session, p.id)


def test_ensure_unlocked(session):
    p = projects.create_project(session, "C", "A", Decimal("1"), None, None)
    e = _entry(session, p.id)
    guards.ensure_unlocked(e)  # no raise
    e.invoice_id = 1
    with pytest.raises(guards.EntryLockedError):
        guards.ensure_unlocked(e)
