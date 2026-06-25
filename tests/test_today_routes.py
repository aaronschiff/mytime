def _setup(client):
    client.post("/projects/new", data={"client_name": "Acme", "name": "Site",
                "hourly_rate": "150", "budget": "", "description": ""}, follow_redirects=False)
    client.post("/settings/task-types", data={"name": "Analysis"}, follow_redirects=False)


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
