def _project(client):
    client.post("/projects/new", data={"client_name": "Acme", "name": "Site",
                "hourly_rate": "150", "budget": "", "description": ""}, follow_redirects=False)
    client.post("/settings/task-types", data={"name": "Analysis"}, follow_redirects=False)


def test_create_entry_and_list(client):
    _project(client)
    r = client.post("/time/new", data={"project_id": "1", "task_type_id": "1",
        "entry_date": "2026-06-25", "duration": "1:30", "notes": "x"},
        follow_redirects=False)
    assert r.status_code == 303
    page = client.get("/time")
    assert "01:30" in page.text
    assert client.get("/projects/1").text.count("01:30") >= 1


def test_edit_locked_entry_returns_403(client):
    _project(client)
    client.post("/time/new", data={"project_id": "1", "task_type_id": "1",
        "entry_date": "2026-06-25", "duration": "1:00", "notes": ""},
        follow_redirects=False)
    # Manually lock the entry via the DB session
    from mytime.main import app
    from mytime.db import get_session
    with next(app.dependency_overrides[get_session]()) as s:
        from mytime.models import TimeEntry
        e = s.get(TimeEntry, 1)
        e.invoice_id = 999
        s.commit()
    assert client.get("/time/1/edit").status_code == 403
    r = client.post("/time/1/edit", data={"project_id": "1", "task_type_id": "1",
        "entry_date": "2026-06-25", "duration": "2:00", "notes": ""},
        follow_redirects=False)
    assert r.status_code == 403
