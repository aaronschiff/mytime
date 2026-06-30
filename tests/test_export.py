import csv
import io
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from mytime import clock, format
from mytime.models import Invoice, TimeEntry
from mytime.services import export, projects, task_types, time_entries, timers


def _seed(session):
    project = projects.create_project(
        session, "Acme Co", "Website", hourly_rate=Decimal("100"),
        budget=None, description=None,
    )
    task = task_types.add_task_type(session, "Development")
    entry = time_entries.create_entry(
        session, project.id, task.id, date(2026, 1, 5), seconds=3600, notes="Initial build",
    )
    return project, task, entry


def test_csv_rows_for_stopped_entry(session):
    project, task, entry = _seed(session)

    rows = export.time_entries_csv_rows(session)

    assert len(rows) == 1
    row = rows[0]
    assert row["entry_id"] == entry.id
    assert row["date"] == "2026-01-05"
    assert row["created_at"] == format.fmt_datetime(clock.to_local(entry.created_at))
    assert row["client"] == "Acme Co"
    assert row["project"] == "Website"
    assert row["task_type"] == "Development"
    assert row["notes"] == "Initial build"
    assert row["hourly_rate"] == Decimal("100.00")
    assert row["hours"] == Decimal("1.00")
    assert row["amount"] == Decimal("100.00")
    assert row["invoice_number"] == ""
    assert row["running"] == "No"
    assert row["project_status"] == "active"


def test_csv_rows_use_live_elapsed_for_running_timer(session):
    project, task, entry = _seed(session)
    timers.start_timer(session, entry.id, datetime(2026, 1, 5, 9, 0, 0))

    rows = export.time_entries_csv_rows(session, at=datetime(2026, 1, 5, 10, 30, 0))

    row = rows[0]
    assert row["running"] == "Yes"
    # 1 banked hour (seeded) + 1.5 hours of live running time
    assert row["hours"] == Decimal("2.50")
    assert row["amount"] == Decimal("250.00")


def test_csv_rows_created_at_converted_to_local_time(session, monkeypatch):
    monkeypatch.setattr(clock, "_TZ", ZoneInfo("Pacific/Auckland"))

    project, task, entry = _seed(session)
    entry.created_at = datetime(2026, 1, 5, 1, 30, 0)  # 01:30 UTC = 14:30 NZDT
    session.commit()

    rows = export.time_entries_csv_rows(session)

    assert rows[0]["created_at"] == "2026-01-05 14:30"


def test_csv_rows_reflect_invoice_number(session):
    project, task, entry = _seed(session)
    invoice = Invoice(
        project_id=project.id, cutoff_date=date(2026, 1, 6),
        rate_snapshot=Decimal("100"), total_amount=Decimal("100"),
        invoice_number="INV-001",
    )
    session.add(invoice)
    session.commit()
    entry.invoice_id = invoice.id
    session.commit()

    rows = export.time_entries_csv_rows(session)

    row = rows[0]
    assert row["invoice_number"] == "INV-001"


def test_csv_rows_ordered_by_date_and_created_at(session):
    project = projects.create_project(
        session, "Acme Co", "Website", hourly_rate=Decimal("100"),
        budget=None, description=None,
    )
    task = task_types.add_task_type(session, "Development")

    def _entry(entry_date, created_at):
        e = TimeEntry(
            project_id=project.id, task_type_id=task.id, entry_date=entry_date,
            seconds=60, created_at=created_at,
        )
        session.add(e)
        session.commit()
        return e

    # Created out of order, on purpose, to prove the export re-sorts them.
    later_date = _entry(date(2026, 1, 2), datetime(2026, 1, 2, 10, 0, 0))
    late_created = _entry(date(2026, 1, 1), datetime(2026, 1, 1, 14, 0, 0))
    early_created = _entry(date(2026, 1, 1), datetime(2026, 1, 1, 9, 0, 0))

    rows = export.time_entries_csv_rows(session)

    assert [r["entry_id"] for r in rows] == [
        early_created.id, late_created.id, later_date.id,
    ]


def test_csv_rows_empty_database(session):
    assert export.time_entries_csv_rows(session) == []


def test_export_route_returns_csv(client):
    client.post("/projects", data={
        "client_name": "Acme Co", "name": "Website", "hourly_rate": "100",
        "budget": "", "description": "",
    }, follow_redirects=False)
    client.post("/settings/task-types", data={"name": "Development"}, follow_redirects=False)

    resp = client.get("/settings/export")

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert ".csv" in resp.headers["content-disposition"]
    reader = csv.reader(io.StringIO(resp.text))
    header = next(reader)
    assert header == [
        "entry_id", "date", "created_at", "client", "project", "task_type", "notes",
        "hourly_rate", "hours", "amount", "invoice_number",
        "running", "project_status",
    ]
    assert list(reader) == []
