def _setup(client):
    client.post("/projects/new", data={"client_name": "Acme", "name": "Site",
                "hourly_rate": "150", "budget": "", "description": ""}, follow_redirects=False)
    client.post("/settings/task-types", data={"name": "Analysis"}, follow_redirects=False)


def test_add_with_invalid_duration_is_rejected(client):
    """A duration the server can't parse must not be silently saved as a
    0-second entry — that's lost time. Reject with an error instead."""
    from mytime.models import TimeEntry
    _setup(client)
    r = client.post("/today/add", data={"project_id": "1", "task_type_id": "1",
                    "notes": "", "duration": "2:99", "start": "0"}, follow_redirects=False)
    assert r.status_code == 400
    assert "duration" in r.text.lower()
    for dep in client.app.dependency_overrides.values():
        gen = dep(); s = next(gen)
        assert s.query(TimeEntry).count() == 0  # nothing created
        break


def test_add_timer_and_stop(client):
    _setup(client)
    assert client.get("/today").status_code == 200
    r = client.post("/today/add", data={"project_id": "1", "task_type_id": "1", "notes": ""},
                    follow_redirects=False)
    assert r.status_code == 303
    page = client.get("/today")
    assert "running" in page.text  # the row is running
    stop = client.post("/today/1/stop")            # returns the partial
    assert stop.status_code == 200
    assert "Start" in stop.text                    # now stopped


def test_today_body_returns_running_partial(client):
    """GET /today/body returns just the timer-list partial (not the full
    page), reflecting current server state — this is what the cross-device
    poll and the tab-focus refresh fetch."""
    _setup(client)
    client.post("/today/add", data={"project_id": "1", "task_type_id": "1", "notes": ""},
                follow_redirects=False)
    r = client.get("/today/body")
    assert r.status_code == 200
    assert "Stop" in r.text                  # the running timer shows its Stop control
    assert "<html" not in r.text.lower()     # partial only — no full-page shell/nav
