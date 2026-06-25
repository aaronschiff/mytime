from datetime import datetime, date
from decimal import Decimal
from mytime import clock
from mytime.services import timers, projects, task_types


def _setup(session):
    p = projects.create_project(session, "C", "A", Decimal("1"), None, None)
    t = task_types.add_task_type(session, "Analysis")
    return p, t


def test_add_timer_autostarts(session):
    p, t = _setup(session)
    at = datetime(2026, 6, 25, 9, 0, 0)
    e = timers.add_timer(session, p.id, t.id, None, at)
    assert e.running_since == at
    assert e.first_started_at == at
    assert e.entry_date == clock.today()
    assert timers.running_timer(session).id == e.id


def test_starting_one_stops_the_other(session):
    p, t = _setup(session)
    a = timers.add_timer(session, p.id, t.id, None, datetime(2026, 6, 25, 9, 0, 0))
    b = timers.add_timer(session, p.id, t.id, None, datetime(2026, 6, 25, 9, 10, 0))
    session.refresh(a)
    assert a.running_since is None          # auto-stopped when b was added
    assert a.seconds == 600                 # 10 minutes folded in
    assert timers.running_timer(session).id == b.id


def test_stop_folds_elapsed(session):
    p, t = _setup(session)
    e = timers.add_timer(session, p.id, t.id, None, datetime(2026, 6, 25, 9, 0, 0))
    timers.stop_timer(session, e.id, datetime(2026, 6, 25, 9, 5, 0))
    assert e.seconds == 300 and e.running_since is None


def test_live_elapsed_includes_running_delta(session):
    p, t = _setup(session)
    e = timers.add_timer(session, p.id, t.id, None, datetime(2026, 6, 25, 9, 0, 0))
    assert timers.live_elapsed(e, datetime(2026, 6, 25, 9, 0, 42)) == 42


def test_restart_keeps_first_started_at(session):
    p, t = _setup(session)
    e = timers.add_timer(session, p.id, t.id, None, datetime(2026, 6, 25, 9, 0, 0))
    timers.stop_timer(session, e.id, datetime(2026, 6, 25, 9, 1, 0))
    timers.start_timer(session, e.id, datetime(2026, 6, 25, 10, 0, 0))
    assert e.first_started_at == datetime(2026, 6, 25, 9, 0, 0)


def test_todays_timers_sorted_by_first_start(session):
    p, t = _setup(session)
    a = timers.add_timer(session, p.id, t.id, None, datetime(2026, 6, 25, 9, 0, 0))
    b = timers.add_timer(session, p.id, t.id, None, datetime(2026, 6, 25, 8, 0, 0))
    ids = [e.id for e in timers.todays_timers(session, clock.today())]
    # b started earlier in wall-clock but was added second; order by first_started_at
    assert ids == [a.id, b.id]
