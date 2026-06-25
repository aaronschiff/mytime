def _project(client):
    client.post("/projects/new", data={"client_name": "Acme", "name": "Site",
                "hourly_rate": "150", "budget": "", "description": ""}, follow_redirects=False)
    client.post("/settings/task-types", data={"name": "Analysis"}, follow_redirects=False)


def test_create_entry_and_list(client):
    _project(client)
    r = client.post("/time/new", data={"project_id": "1", "task_type_id": "1",
        "entry_date": "2026-06-25", "hours": "1", "minutes": "30", "notes": "x"},
        follow_redirects=False)
    assert r.status_code == 303
    page = client.get("/time")
    assert "1h 30m" in page.text
    assert client.get("/projects/1").text.count("1h 30m") >= 1
