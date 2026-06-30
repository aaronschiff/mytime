"""clock.now() must return naive UTC, so elapsed-time math is independent of the
server's OS timezone and immune to DST transitions."""
from datetime import datetime, timezone

from mytime import clock


def test_now_returns_naive_utc():
    before = datetime.now(timezone.utc).replace(tzinfo=None)
    value = clock.now()
    after = datetime.now(timezone.utc).replace(tzinfo=None)
    assert value.tzinfo is None  # naive, per the storage convention
    # Must track UTC wall-clock, not OS-local time. On a non-UTC host the old
    # datetime.now() impl would be off by the UTC offset and fail this.
    assert before <= value <= after
