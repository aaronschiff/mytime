from decimal import Decimal
from datetime import date
from mytime.models import Project, TaskType, TimeEntry


def test_project_and_entry_roundtrip(session):
    p = Project(client_name="Acme", name="Website", hourly_rate=Decimal("150.00"))
    t = TaskType(name="Analysis")
    session.add_all([p, t])
    session.flush()
    e = TimeEntry(project_id=p.id, task_type_id=t.id, entry_date=date(2026, 6, 25), seconds=3600)
    session.add(e)
    session.commit()

    got = session.get(TimeEntry, e.id)
    assert got.seconds == 3600
    assert got.invoice_id is None
    assert session.get(Project, p.id).hourly_rate == Decimal("150.00")
