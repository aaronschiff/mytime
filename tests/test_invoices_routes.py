def _setup(client):
    client.post("/projects/new", data={"client_name": "Acme", "name": "Site",
                "hourly_rate": "100", "budget": "1000", "description": ""}, follow_redirects=False)
    client.post("/settings/task-types", data={"name": "Analysis"}, follow_redirects=False)
    client.post("/time/new", data={"project_id": "1", "task_type_id": "1",
                "entry_date": "2026-06-20", "duration": "2:00", "notes": ""},
                follow_redirects=False)


def test_build_create_view_void(client):
    _setup(client)
    build = client.get("/projects/1/invoices/new?cutoff=2026-06-30")
    assert "Analysis" in build.text
    r = client.post("/projects/1/invoices/new",
                    data={"cutoff": "2026-06-30", "task_id": "1", "duration_1": "2:00"},
                    follow_redirects=False)
    assert r.status_code == 303
    inv_url = r.headers["location"]
    view = client.get(inv_url)
    assert "$200" in view.text
    # entry now locked — not offered again
    assert "No uninvoiced time" in client.get("/projects/1/invoices/new?cutoff=2026-06-30").text
    # void
    inv_id = inv_url.rsplit("/", 1)[1]
    client.post(f"/invoices/{inv_id}/void", follow_redirects=False)
    assert "Analysis" in client.get("/projects/1/invoices/new?cutoff=2026-06-30").text


def _fixed_setup(client):
    client.post("/projects/new", data={"client_name": "Acme", "name": "Fixed",
                "hourly_rate": "200", "budget": "45000", "description": "",
                "billing_type": "fixed"}, follow_redirects=False)


def test_fixed_invoice_flow(client):
    _fixed_setup(client)
    build = client.get("/projects/1/invoices/new")
    assert "Fixed-fee project" in build.text
    assert "Task" not in build.text  # no task/seconds grid
    r = client.post("/projects/1/invoices/new",
                    data={"amount": "15000", "label": "Inception",
                          "invoice_date": "2026-06-30", "invoice_number": "1"},
                    follow_redirects=False)
    assert r.status_code == 303
    view = client.get(r.headers["location"])
    assert "15,000" in view.text
    assert "Inception" in view.text


def test_fixed_invoice_rejects_bad_amount(client):
    _fixed_setup(client)
    r = client.post("/projects/1/invoices/new",
                    data={"amount": "abc", "label": "", "invoice_date": "2026-06-30"},
                    follow_redirects=False)
    assert r.status_code == 400
    assert "valid invoice amount" in r.text
