from decimal import Decimal
from mytime.services import projects


def test_create_and_get(session):
    p = projects.create_project(session, "Acme", "Site", Decimal("150"), Decimal("5000"), "notes")
    got = projects.get_project(session, p.id)
    assert got.client_name == "Acme"
    assert got.status == "active"
    assert got.budget == Decimal("5000")


def test_create_without_budget(session):
    p = projects.create_project(session, "Acme", "Internal", Decimal("0"), None, None)
    assert p.budget is None


def test_list_filters_by_status(session):
    a = projects.create_project(session, "C", "A", Decimal("1"), None, None)
    projects.create_project(session, "C", "B", Decimal("1"), None, None)
    projects.set_status(session, a.id, "archived")
    assert len(projects.list_projects(session, status="active")) == 1
    assert len(projects.list_projects(session, status="archived")) == 1
    assert len(projects.list_projects(session)) == 2


def test_update(session):
    p = projects.create_project(session, "C", "A", Decimal("1"), None, None)
    projects.update_project(session, p.id, "C2", "A2", Decimal("99"), Decimal("100"), "n")
    got = projects.get_project(session, p.id)
    assert got.client_name == "C2" and got.hourly_rate == Decimal("99")
