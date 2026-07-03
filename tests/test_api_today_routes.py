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


def test_create_entry_start_now(client):
    _setup(client)
    r = client.post("/api/today/entries", json={
        "project_id": 1, "task_type_id": 1, "notes": "started", "start": True,
    })
    assert r.status_code == 200
    body = r.json()
    assert len(body["entries"]) == 1
    assert body["entries"][0]["running"] is True
    assert body["entries"][0]["notes"] == "started"


def test_create_entry_save_duration(client):
    _setup(client)
    r = client.post("/api/today/entries", json={
        "project_id": 1, "task_type_id": 1, "notes": "logged", "start": False, "duration": "1:30",
    })
    assert r.status_code == 200
    body = r.json()
    assert len(body["entries"]) == 1
    e = body["entries"][0]
    assert e["running"] is False
    assert e["base_seconds"] == 90 * 60
    assert e["notes"] == "logged"


def test_create_entry_bad_duration_is_400(client):
    _setup(client)
    r = client.post("/api/today/entries", json={
        "project_id": 1, "task_type_id": 1, "notes": "", "start": False, "duration": "2:99",
    })
    assert r.status_code == 400
    assert "error" in r.json()
    assert client.get("/api/today").json()["entries"] == []  # nothing created


def test_start_stops_other_running_timer(client):
    """Single-running-timer invariant, enforced server-side in stop_all_running.
    Entry 1 is left RUNNING (not stopped first) and entry 2 is created stopped
    (start=False, so creating it doesn't itself touch entry 1) — only the
    explicit /start call on entry 2 should stop entry 1."""
    _setup(client)
    client.post("/today/add", data={"project_id": "1", "task_type_id": "1", "notes": "first"},
                follow_redirects=False)  # entry 1: running
    client.post("/api/today/entries", json={"project_id": 1, "task_type_id": 1,
                "notes": "second", "start": False, "duration": "1:00"})  # entry 2: stopped
    r = client.post("/api/today/2/start")
    assert r.status_code == 200
    entries = {e["id"]: e for e in r.json()["entries"]}
    assert entries[2]["running"] is True
    assert entries[1]["running"] is False


def test_stop_running_entry(client):
    _setup(client)
    client.post("/today/add", data={"project_id": "1", "task_type_id": "1", "notes": ""},
                follow_redirects=False)
    r = client.post("/api/today/1/stop")
    assert r.status_code == 200
    assert r.json()["entries"][0]["running"] is False


def test_start_unknown_entry_is_404(client):
    _setup(client)
    r = client.post("/api/today/999/start")
    assert r.status_code == 404
    assert "error" in r.json()


def test_stop_unknown_entry_is_404(client):
    _setup(client)
    r = client.post("/api/today/999/stop")
    assert r.status_code == 404
    assert "error" in r.json()


def test_start_locked_entry_is_403(client):
    _setup(client)
    client.post("/today/add", data={"project_id": "1", "task_type_id": "1", "notes": ""},
                follow_redirects=False)
    client.post("/today/1/stop")
    _lock_entry(client, 1)
    r = client.post("/api/today/1/start")
    assert r.status_code == 403
    assert "error" in r.json()


def test_stop_locked_entry_is_403(client):
    _setup(client)
    client.post("/today/add", data={"project_id": "1", "task_type_id": "1", "notes": ""},
                follow_redirects=False)
    _lock_entry(client, 1)
    r = client.post("/api/today/1/stop")
    assert r.status_code == 403
    assert "error" in r.json()


def test_set_time_updates_stopped_entry(client):
    _setup(client)
    client.post("/today/add", data={"project_id": "1", "task_type_id": "1", "notes": ""},
                follow_redirects=False)
    client.post("/today/1/stop")
    r = client.post("/api/today/1/set-time", json={"time_hm": "2:15"})
    assert r.status_code == 200
    assert r.json()["entries"][0]["base_seconds"] == (2 * 3600 + 15 * 60)


def test_set_time_rejects_bad_format(client):
    _setup(client)
    client.post("/today/add", data={"project_id": "1", "task_type_id": "1", "notes": ""},
                follow_redirects=False)
    client.post("/today/1/stop")
    r = client.post("/api/today/1/set-time", json={"time_hm": "2:99"})
    assert r.status_code == 400
    assert "error" in r.json()


def test_set_time_rejects_running_entry(client):
    _setup(client)
    client.post("/today/add", data={"project_id": "1", "task_type_id": "1", "notes": ""},
                follow_redirects=False)
    r = client.post("/api/today/1/set-time", json={"time_hm": "2:00"})
    assert r.status_code == 403
    assert "error" in r.json()


def test_set_time_rejects_locked_entry(client):
    _setup(client)
    client.post("/today/add", data={"project_id": "1", "task_type_id": "1", "notes": ""},
                follow_redirects=False)
    client.post("/today/1/stop")
    _lock_entry(client, 1)
    r = client.post("/api/today/1/set-time", json={"time_hm": "2:00"})
    assert r.status_code == 403
    assert "error" in r.json()


def test_set_time_unknown_entry_is_404(client):
    _setup(client)
    r = client.post("/api/today/999/set-time", json={"time_hm": "2:00"})
    assert r.status_code == 404


def test_edit_updates_stopped_entry(client):
    _setup(client)
    client.post("/settings/task-types", data={"name": "Design"}, follow_redirects=False)
    client.post("/today/add", data={"project_id": "1", "task_type_id": "1", "notes": "old"},
                follow_redirects=False)
    client.post("/today/1/stop")
    r = client.post("/api/today/1/edit", json={
        "project_id": 1, "task_type_id": 2, "duration": "3:00", "notes": "new",
    })
    assert r.status_code == 200
    e = r.json()["entries"][0]
    assert e["task_type_id"] == 2
    assert e["base_seconds"] == 3 * 3600
    assert e["notes"] == "new"


def test_edit_auto_stops_running_entry(client):
    _setup(client)
    client.post("/today/add", data={"project_id": "1", "task_type_id": "1", "notes": ""},
                follow_redirects=False)
    r = client.post("/api/today/1/edit", json={
        "project_id": 1, "task_type_id": 1, "duration": "1:00", "notes": "edited",
    })
    assert r.status_code == 200
    e = r.json()["entries"][0]
    assert e["running"] is False
    assert e["base_seconds"] == 3600


def test_edit_bad_duration_is_400(client):
    _setup(client)
    client.post("/today/add", data={"project_id": "1", "task_type_id": "1", "notes": ""},
                follow_redirects=False)
    client.post("/today/1/stop")
    r = client.post("/api/today/1/edit", json={
        "project_id": 1, "task_type_id": 1, "duration": "9:99", "notes": "",
    })
    assert r.status_code == 400
    assert "error" in r.json()


def test_edit_locked_entry_is_403(client):
    _setup(client)
    client.post("/today/add", data={"project_id": "1", "task_type_id": "1", "notes": ""},
                follow_redirects=False)
    client.post("/today/1/stop")
    _lock_entry(client, 1)
    r = client.post("/api/today/1/edit", json={
        "project_id": 1, "task_type_id": 1, "duration": "1:00", "notes": "",
    })
    assert r.status_code == 403
    assert "error" in r.json()


def test_edit_archived_project_is_403(client):
    _setup(client)
    client.post("/today/add", data={"project_id": "1", "task_type_id": "1", "notes": ""},
                follow_redirects=False)
    client.post("/today/1/stop")
    client.post("/projects/1/status", data={"status": "archived"}, follow_redirects=False)
    r = client.post("/api/today/1/edit", json={
        "project_id": 1, "task_type_id": 1, "duration": "1:00", "notes": "",
    })
    assert r.status_code == 403
    assert "error" in r.json()


def test_edit_unknown_entry_is_404(client):
    _setup(client)
    r = client.post("/api/today/999/edit", json={
        "project_id": 1, "task_type_id": 1, "duration": "1:00", "notes": "",
    })
    assert r.status_code == 404


def test_delete_entry(client):
    _setup(client)
    client.post("/today/add", data={"project_id": "1", "task_type_id": "1", "notes": ""},
                follow_redirects=False)
    client.post("/today/1/stop")
    r = client.delete("/api/today/1")
    assert r.status_code == 200
    assert r.json()["entries"] == []


def test_delete_locked_entry_is_403(client):
    _setup(client)
    client.post("/today/add", data={"project_id": "1", "task_type_id": "1", "notes": ""},
                follow_redirects=False)
    client.post("/today/1/stop")
    _lock_entry(client, 1)
    r = client.delete("/api/today/1")
    assert r.status_code == 403
    assert "error" in r.json()
    assert len(client.get("/api/today").json()["entries"]) == 1  # not deleted


def test_delete_unknown_entry_is_404(client):
    _setup(client)
    r = client.delete("/api/today/999")
    assert r.status_code == 404
