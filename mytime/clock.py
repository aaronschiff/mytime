from datetime import datetime, date, timezone
import os
from zoneinfo import ZoneInfo

_tz_name = os.environ.get("MYTIME_TIMEZONE")
_TZ = ZoneInfo(_tz_name) if _tz_name else None


def now() -> datetime:
    """Current instant as a naive UTC datetime.

    All datetimes in the app are stored and compared as naive UTC, so duration
    math (e.g. timers.live_elapsed) is independent of the server's OS timezone
    and immune to DST transitions. Local calendar dates use today() instead.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def today() -> date:
    if _TZ is not None:
        return datetime.now(_TZ).date()
    return date.today()


def to_local(dt: datetime) -> datetime:
    """Convert a naive UTC datetime (the storage convention) to naive local
    wall-clock time for display, using MYTIME_TIMEZONE if set, otherwise the
    OS local timezone — mirrors today()'s fallback."""
    return dt.replace(tzinfo=timezone.utc).astimezone(_TZ).replace(tzinfo=None)
