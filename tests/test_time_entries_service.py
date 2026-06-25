import pytest
from decimal import Decimal
from datetime import date
from mytime.services import time_entries as te, projects, task_types, guards


def _setup(session):
    p = projects.create_project(session, "C", "A", Decimal("1"), None, None)
    t = task_types.add_task_type(session, "Analysis")
    return p, t


def test_create_and_list(session):
    p, t = _setup(session)
    te.create_entry(session, p.id, t.id, date(2026, 6, 25), 3600, "did stuff")
    te.create_entry(session, p.id, t.id, date(2026, 6, 26), 1800, None)
    rows = te.list_entries(session, project_id=p.id)
    assert [r.entry_date for r in rows] == [date(2026, 6, 26), date(2026, 6, 25)]


def test_update_and_delete(session):
    p, t = _setup(session)
    e = te.create_entry(session, p.id, t.id, date(2026, 6, 25), 3600, None)
    te.update_entry(session, e.id, t.id, date(2026, 6, 25), 7200, "edited")
    assert te.get_entry(session, e.id).seconds == 7200
    te.delete_entry(session, e.id)
    assert te.get_entry(session, e.id) is None


def test_locked_entry_rejects_edit_and_delete(session):
    p, t = _setup(session)
    e = te.create_entry(session, p.id, t.id, date(2026, 6, 25), 3600, None)
    e.invoice_id = 1
    session.commit()
    with pytest.raises(guards.EntryLockedError):
        te.update_entry(session, e.id, t.id, date(2026, 6, 25), 10, None)
    with pytest.raises(guards.EntryLockedError):
        te.delete_entry(session, e.id)
