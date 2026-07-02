import pytest
from decimal import Decimal
from datetime import date, datetime
from mytime.services import invoicing, projects, task_types, time_entries as te


def _setup(session):
    p = projects.create_project(session, "C", "A", Decimal("100"), Decimal("1000"), None)
    analysis = task_types.add_task_type(session, "Analysis")
    meetings = task_types.add_task_type(session, "Meetings")
    return p, analysis, meetings


def test_preview_groups_by_task(session):
    p, a, m = _setup(session)
    te.create_entry(session, p.id, a.id, date(2026, 6, 20), 3600, None)
    te.create_entry(session, p.id, a.id, date(2026, 6, 21), 1800, None)
    te.create_entry(session, p.id, m.id, date(2026, 6, 22), 600, None)
    te.create_entry(session, p.id, a.id, date(2026, 7, 1), 9999, None)   # after cutoff
    rows = invoicing.build_invoice_preview(session, p.id, date(2026, 6, 30))
    by = {r.task_name: r.tracked_seconds for r in rows}
    assert by == {"Analysis": 5400, "Meetings": 600}


def test_create_invoice_locks_entries_and_snapshots_rate(session):
    p, a, m = _setup(session)
    e1 = te.create_entry(session, p.id, a.id, date(2026, 6, 20), 3600, None)
    e2 = te.create_entry(session, p.id, m.id, date(2026, 6, 22), 3600, None)
    # invoice analysis at 1h, write meetings down to 0
    inv = invoicing.create_invoice(session, p.id, date(2026, 6, 30),
                                   {a.id: 3600, m.id: 0}, datetime(2026, 6, 30, 17, 0, 0))
    assert inv.rate_snapshot == Decimal("100.00")
    assert inv.total_amount == Decimal("100.00")           # 1h@100 + 0
    assert te.get_entry(session, e1.id).invoice_id == inv.id
    assert te.get_entry(session, e2.id).invoice_id == inv.id
    # nothing left to invoice
    assert invoicing.build_invoice_preview(session, p.id, date(2026, 6, 30)) == []


def test_void_unlocks_entries(session):
    p, a, m = _setup(session)
    e1 = te.create_entry(session, p.id, a.id, date(2026, 6, 20), 3600, None)
    inv = invoicing.create_invoice(session, p.id, date(2026, 6, 30), {a.id: 3600},
                                   datetime(2026, 6, 30, 17, 0, 0))
    invoicing.void_invoice(session, inv.id)
    assert te.get_entry(session, e1.id).invoice_id is None
    assert invoicing.get_invoice(session, inv.id) is None
    assert invoicing.list_invoices(session, p.id) == []


def test_running_entries_excluded_from_preview(session):
    from mytime.services import timers
    p, a, m = _setup(session)
    timers.add_timer(session, p.id, a.id, None, datetime(2026, 6, 25, 9, 0, 0))  # running
    assert invoicing.build_invoice_preview(session, p.id, date(2026, 6, 30)) == []


def _fixed_setup(session):
    p = projects.create_project(session, "C", "Fixed", Decimal("200"), Decimal("45000"),
                                None, billing_type="fixed")
    a = task_types.add_task_type(session, "Analysis")
    return p, a


def test_fixed_invoice_flat_amount_no_lines_and_leaves_time(session):
    p, a = _fixed_setup(session)
    e = te.create_entry(session, p.id, a.id, date(2026, 6, 20), 3600, None)
    inv = invoicing.create_fixed_invoice(session, p.id, Decimal("15000"),
                                         datetime(2026, 6, 30, 17, 0, 0), label="Inception")
    assert inv.total_amount == Decimal("15000.00")
    assert inv.label == "Inception"
    assert invoicing.invoice_lines(session, inv.id) == []
    # tracked time untouched — still editable, still counted as uninvoiced
    assert te.get_entry(session, e.id).invoice_id is None


def test_fixed_invoice_computes_gst(session):
    p = projects.create_project(session, "C", "FixedGst", Decimal("200"), Decimal("45000"),
                                None, gst_enabled=True, gst_rate=Decimal("15"),
                                billing_type="fixed")
    inv = invoicing.create_fixed_invoice(session, p.id, Decimal("15000"),
                                         datetime(2026, 6, 30, 17, 0, 0))
    assert inv.total_amount == Decimal("15000.00")
    assert inv.gst_amount == Decimal("2250.00")


def test_void_fixed_invoice(session):
    p, a = _fixed_setup(session)
    inv = invoicing.create_fixed_invoice(session, p.id, Decimal("15000"),
                                         datetime(2026, 6, 30, 17, 0, 0))
    invoicing.void_invoice(session, inv.id)
    assert invoicing.get_invoice(session, inv.id) is None
    assert invoicing.list_invoices(session, p.id) == []
