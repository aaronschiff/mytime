def _make(client, **over):
    data = {"client_name": "Acme", "name": "Site", "hourly_rate": "150", "budget": "", "description": ""}
    data.update(over)
    return client.post("/projects/new", data=data, follow_redirects=False)


def test_create_and_detail(client):
    r = _make(client)
    assert r.status_code == 303
    loc = r.headers["location"]
    assert client.get(loc).status_code == 200
    assert "Acme" in client.get("/projects").text


def test_archive_filter(client):
    _make(client)
    page = client.get("/projects?status=archived")
    assert page.status_code == 200


def test_delete_blocked_with_invoice(client):
    from mytime.models import Invoice
    from decimal import Decimal
    from datetime import date
    _make(client)
    # Insert an invoice for project 1 through the override session
    for dep in client.app.dependency_overrides.values():
        gen = dep(); s = next(gen)
        s.add(Invoice(project_id=1, cutoff_date=date(2026, 6, 25),
                      rate_snapshot=Decimal("1"), total_amount=Decimal("0")))
        s.commit()
        break
    r = client.post("/projects/1/delete", follow_redirects=False)
    assert r.status_code == 409
