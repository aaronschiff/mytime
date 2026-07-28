from mytime import clock


def _project(client):
    client.post("/projects/new", data={"client_name": "Acme", "name": "Site",
                "hourly_rate": "150", "budget": "", "description": ""}, follow_redirects=False)
    client.post("/settings/task-types", data={"name": "Analysis"}, follow_redirects=False)


def test_create_entry_and_list(client):
    _project(client)
    r = client.post("/time/new", data={"project_id": "1", "task_type_id": "1",
        "entry_date": clock.today().isoformat(), "duration": "1:30", "notes": "x"},
        follow_redirects=False)
    assert r.status_code == 303
    page = client.get("/time")
    assert "01:30" in page.text
    assert client.get("/projects/1").text.count("01:30") >= 1


def _entry(client, entry_id=1):
    from mytime.main import app
    from mytime.db import get_session
    from mytime.models import TimeEntry
    with next(app.dependency_overrides[get_session]()) as s:
        e = s.get(TimeEntry, entry_id)
        return e.seconds, e.running_since


def _set_seconds(client, entry_id, seconds):
    from mytime.main import app
    from mytime.db import get_session
    from mytime.models import TimeEntry
    with next(app.dependency_overrides[get_session]()) as s:
        s.get(TimeEntry, entry_id).seconds = seconds
        s.commit()


def test_edit_page_does_not_stop_running_timer(client):
    _project(client)
    client.post("/today/add", data={"project_id": "1", "task_type_id": "1", "notes": ""},
                follow_redirects=False)
    assert client.get("/time/1/edit").status_code == 200
    _, running_since = _entry(client)
    assert running_since is not None


def test_edit_post_keeps_timer_running_with_new_duration(client):
    _project(client)
    client.post("/today/add", data={"project_id": "1", "task_type_id": "1", "notes": ""},
                follow_redirects=False)
    _, since_before = _entry(client)
    r = client.post("/time/1/edit", data={"project_id": "1", "task_type_id": "1",
        "entry_date": clock.today().isoformat(), "duration": "2:00",
        "duration_prefill": "00:00", "notes": ""}, follow_redirects=False)
    assert r.status_code == 303
    seconds, running_since = _entry(client)
    assert seconds == 2 * 3600
    # Still running, and the run restarts at the edit: the new duration is
    # "total as of now", so keeping the old running_since would double-count.
    assert running_since is not None
    assert running_since > since_before


def test_edit_post_unchanged_duration_leaves_time_untouched(client):
    _project(client)
    client.post("/today/add", data={"project_id": "1", "task_type_id": "1", "notes": ""},
                follow_redirects=False)
    _set_seconds(client, 1, 7223)  # displays as 02:00 — a rewrite would floor it to 7200
    _, since_before = _entry(client)
    r = client.post("/time/1/edit", data={"project_id": "1", "task_type_id": "1",
        "entry_date": clock.today().isoformat(), "duration": "02:00",
        "duration_prefill": "02:00", "notes": "note change only"}, follow_redirects=False)
    assert r.status_code == 303
    seconds, running_since = _entry(client)
    assert seconds == 7223
    assert running_since == since_before


def test_edit_locked_entry_returns_403(client):
    _project(client)
    client.post("/time/new", data={"project_id": "1", "task_type_id": "1",
        "entry_date": "2026-06-25", "duration": "1:00", "notes": ""},
        follow_redirects=False)
    # Manually lock the entry via the DB session
    from datetime import date
    from decimal import Decimal
    from mytime.main import app
    from mytime.db import get_session
    with next(app.dependency_overrides[get_session]()) as s:
        from mytime.models import Invoice, TimeEntry
        e = s.get(TimeEntry, 1)
        invoice = Invoice(project_id=e.project_id, cutoff_date=date(2026, 6, 25),
                          rate_snapshot=Decimal("1"), total_amount=Decimal("1"))
        s.add(invoice)
        s.flush()
        e.invoice_id = invoice.id
        s.commit()
    assert client.get("/time/1/edit").status_code == 403
    r = client.post("/time/1/edit", data={"project_id": "1", "task_type_id": "1",
        "entry_date": "2026-06-25", "duration": "2:00", "notes": ""},
        follow_redirects=False)
    assert r.status_code == 403
