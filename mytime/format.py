from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP


def fmt_hm(seconds: int) -> str:
    minutes = (int(seconds) + 30) // 60
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def fmt_hms(seconds: int) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}"


def fmt_date(d) -> str:
    if isinstance(d, datetime):
        d = d.date()
    return d.strftime("%d-%m-%Y")


def parse_hm(hours: int, minutes: int) -> int:
    return int(hours) * 3600 + int(minutes) * 60


def parse_duration(hm: str) -> int:
    """Parse 'hh:mm' or 'h:mm' text input into seconds. Returns 0 for invalid input."""
    hm = (hm or "").strip()
    if ":" not in hm:
        return 0
    parts = hm.split(":", 1)
    try:
        h = int(parts[0])
        m = int(parts[1])
        if h < 0 or m < 0 or m > 59:
            return 0
        return h * 3600 + m * 60
    except (ValueError, IndexError):
        return 0


def money(amount, symbol: str = "$") -> str:
    q = int(Decimal(amount).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return f"{symbol}{q:,}"
