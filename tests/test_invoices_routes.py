def _setup(client):
    client.post("/projects/new", data={"client_name": "Acme", "name": "Site",
                "hourly_rate": "100", "budget": "1000", "description": ""}, follow_redirects=False)
    client.post("/settings/task-types", data={"name": "Analysis"}, follow_redirects=False)
    client.post("/time/new", data={"project_id": "1", "task_type_id": "1",
                "entry_date": "2026-06-20", "hours": "2", "minutes": "0", "notes": ""},
                follow_redirects=False)


def test_build_create_view_void(client):
    _setup(client)
    build = client.get("/projects/1/invoices/new?cutoff=2026-06-30")
    assert "Analysis" in build.text
    r = client.post("/projects/1/invoices/new",
                    data={"cutoff": "2026-06-30", "task_id": "1", "hours_1": "2", "minutes_1": "0"},
                    follow_redirects=False)
    assert r.status_code == 303
    inv_url = r.headers["location"]
    view = client.get(inv_url)
    assert "$200.00" in view.text
    # entry now locked — not offered again
    assert "No uninvoiced time" in client.get("/projects/1/invoices/new?cutoff=2026-06-30").text
    # void
    inv_id = inv_url.rsplit("/", 1)[1]
    client.post(f"/invoices/{inv_id}/void", follow_redirects=False)
    assert "Analysis" in client.get("/projects/1/invoices/new?cutoff=2026-06-30").text
