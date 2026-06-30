"""clock.now() must return naive UTC, so elapsed-time math is independent of the
server's OS timezone and immune to DST transitions."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from mytime import clock


def test_now_returns_naive_utc():
    before = datetime.now(timezone.utc).replace(tzinfo=None)
    value = clock.now()
    after = datetime.now(timezone.utc).replace(tzinfo=None)
    assert value.tzinfo is None  # naive, per the storage convention
    # Must track UTC wall-clock, not OS-local time. On a non-UTC host the old
    # datetime.now() impl would be off by the UTC offset and fail this.
    assert before <= value <= after


def test_to_local_converts_naive_utc_to_configured_timezone(monkeypatch):
    monkeypatch.setattr(clock, "_TZ", ZoneInfo("Pacific/Auckland"))
    # NZDT (Jan, daylight saving) is UTC+13.
    local = clock.to_local(datetime(2026, 1, 5, 1, 30, 0))
    assert local == datetime(2026, 1, 5, 14, 30, 0)
    assert local.tzinfo is None  # naive, for plain formatting/comparison


def test_to_local_falls_back_to_os_timezone_when_unset(monkeypatch):
    monkeypatch.setattr(clock, "_TZ", None)
    utc_dt = datetime(2026, 1, 5, 1, 30, 0)
    expected = utc_dt.replace(tzinfo=timezone.utc).astimezone(None).replace(tzinfo=None)
    assert clock.to_local(utc_dt) == expected
