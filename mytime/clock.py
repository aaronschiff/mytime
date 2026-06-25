from datetime import datetime, date
import os
from zoneinfo import ZoneInfo

_tz_name = os.environ.get("MYTIME_TIMEZONE")
_TZ = ZoneInfo(_tz_name) if _tz_name else None


def now() -> datetime:
    return datetime.now()


def today() -> date:
    if _TZ is not None:
        return datetime.now(_TZ).date()
    return date.today()
