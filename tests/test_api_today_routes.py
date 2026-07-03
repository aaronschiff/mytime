from datetime import date, timedelta


def _setup(client):
    client.post("/projects/new", data={"client_name": "Acme", "name": "Site",
                "hourly_rate": "150", "budget": "", "description": ""}, follow_redirects=False)
    client.post("/settings/task-types", data={"name": "Analysis"}, follow_redirects=False)


def _lock_entry(client, entry_id: int):
    """Manually lock a time entry via a real Invoice row (FK enforcement is on —
    invoice_id must reference a real row, see tests/test_time_routes.py precedent)."""
    from datetime import date as _date
    from decimal import Decimal
    from mytime.main import app
    from mytime.db import get_session
    from mytime.models import Invoice, TimeEntry
    with next(app.dependency_overrides[get_session]()) as s:
        e = s.get(TimeEntry, entry_id)
        invoice = Invoice(project_id=e.project_id, cutoff_date=_date(2026, 6, 25),
                          rate_snapshot=Decimal("1"), total_amount=Decimal("1"))
        s.add(invoice)
        s.flush()
        e.invoice_id = invoice.id
        s.commit()


def test_get_today_empty_shape(client):
    _setup(client)
    r = client.get("/api/today")
    assert r.status_code == 200
    body = r.json()
    assert body["entries"] == []
    assert body["total_seconds"] == 0
    assert body["week_seconds"] == 0
    assert body["projects"] == [{"id": 1, "name": "Site"}]
    assert body["task_types"] == [{"id": 1, "name": "Analysis"}]
    assert body["day"] == date.today().isoformat() or len(body["day"]) == 10  # YYYY-MM-DD


def test_get_today_running_entry_shape(client):
    _setup(client)
    client.post("/today/add", data={"project_id": "1", "task_type_id": "1", "notes": "hi"},
                follow_redirects=False)
    body = client.get("/api/today").json()
    assert len(body["entries"]) == 1
    e = body["entries"][0]
    assert e["id"] == 1
    assert e["project_id"] == 1
    assert e["project_name"] == "Site"
    assert e["task_type_id"] == 1
    assert e["task_type_name"] == "Analysis"
    assert e["notes"] == "hi"
    assert e["running"] is True
    assert e["since"] is not None and e["since"].endswith("Z")
    assert e["locked"] is False


def test_get_today_stopped_entry_shape(client):
    _setup(client)
    client.post("/today/add", data={"project_id": "1", "task_type_id": "1", "notes": ""},
                follow_redirects=False)
    client.post("/today/1/stop")
    e = client.get("/api/today").json()["entries"][0]
    assert e["running"] is False
    assert e["since"] is None
    assert e["base_seconds"] >= 0


def test_get_today_locked_entry_shape(client):
    _setup(client)
    client.post("/today/add", data={"project_id": "1", "task_type_id": "1", "notes": ""},
                follow_redirects=False)
    client.post("/today/1/stop")
    _lock_entry(client, 1)
    e = client.get("/api/today").json()["entries"][0]
    assert e["locked"] is True
