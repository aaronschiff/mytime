"""Tests for features added in TESTING.md polish pass."""


def _setup(client):
    client.post("/projects/new", data={"client_name": "Acme", "name": "Site",
                "hourly_rate": "100", "budget": "1000", "description": ""}, follow_redirects=False)
    client.post("/settings/task-types", data={"name": "Analysis"}, follow_redirects=False)


def _add_entry(client, duration="2:00"):
    client.post("/time/new", data={"project_id": "1", "task_type_id": "1",
                "entry_date": "2026-06-20", "duration": duration, "notes": ""},
                follow_redirects=False)


def test_today_save_without_start(client):
    """Save mode (start=0) creates entry without starting timer."""
    _setup(client)
    r = client.post("/today/add", data={
        "project_id": "1", "task_type_id": "1", "notes": "",
        "duration": "1:30", "start": "0",
    }, follow_redirects=False)
    assert r.status_code == 303
    page = client.get("/today")
    # The entry was created but not running (no row with class="running")
    assert 'class="running"' not in page.text


def test_today_set_time(client):
    """POST /today/{id}/set-time updates entry seconds."""
    _setup(client)
    # Create a stopped entry
    client.post("/today/add", data={
        "project_id": "1", "task_type_id": "1", "notes": "",
        "duration": "1:00", "start": "0",
    }, follow_redirects=False)
    r = client.post("/today/1/set-time", data={"time_hm": "2:30"})
    assert r.status_code == 200
    assert "02:30" in r.text


def test_invoice_list_page(client):
    """GET /invoices shows invoice list page."""
    _setup(client)
    page = client.get("/invoices")
    assert page.status_code == 200
    assert "Invoices" in page.text


def test_invoice_number_uniqueness(client):
    """Creating two invoices with the same number returns 400."""
    _setup(client)
    _add_entry(client)
    # Create first invoice with number INV-001
    r1 = client.post("/projects/1/invoices/new", data={
        "cutoff": "2026-06-30", "task_id": "1", "duration_1": "2:00",
        "invoice_number": "INV-001",
    }, follow_redirects=False)
    assert r1.status_code == 303

    # Add a second entry (first was locked)
    _add_entry(client, duration="1:00")
    # Try to create another invoice with the same number
    r2 = client.post("/projects/1/invoices/new", data={
        "cutoff": "2026-06-30", "task_id": "1", "duration_1": "1:00",
        "invoice_number": "INV-001",
    }, follow_redirects=False)
    assert r2.status_code == 400
    assert "already exists" in r2.text


def test_invoice_number_in_view(client):
    """Invoice view shows custom invoice number."""
    _setup(client)
    _add_entry(client)
    r = client.post("/projects/1/invoices/new", data={
        "cutoff": "2026-06-30", "task_id": "1", "duration_1": "2:00",
        "invoice_number": "MYINV-007",
    }, follow_redirects=False)
    assert r.status_code == 303
    inv_url = r.headers["location"]
    view = client.get(inv_url)
    assert "MYINV-007" in view.text


def test_projects_list_shows_status(client):
    """Projects list shows status filter visually."""
    _setup(client)
    page = client.get("/projects?status=active")
    assert page.status_code == 200
    assert "active" in page.text


def test_invoice_list_shows_invoices(client):
    """Invoice list shows created invoices."""
    _setup(client)
    _add_entry(client)
    client.post("/projects/1/invoices/new", data={
        "cutoff": "2026-06-30", "task_id": "1", "duration_1": "2:00",
        "invoice_number": "TEST-001",
    }, follow_redirects=False)
    page = client.get("/invoices")
    assert "TEST-001" in page.text
    assert "Acme" in page.text
