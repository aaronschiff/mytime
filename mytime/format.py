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


def fmt_datetime(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M")


def parse_hm(hours: int, minutes: int) -> int:
    return int(hours) * 3600 + int(minutes) * 60


def parse_duration(hm: str) -> int | None:
    """Parse 'hh:mm', plain hours (e.g. '2'), or empty string into seconds.
    Returns None for invalid input (non-numeric, negative, or minutes > 59)."""
    hm = (hm or "").strip()
    if not hm:
        return 0
    if ":" not in hm:
        try:
            h = int(hm)
            if h < 0:
                return None
            return h * 3600
        except ValueError:
            return None
    parts = hm.split(":", 1)
    try:
        h = int(parts[0])
        m = int(parts[1])
        if h < 0 or m < 0 or m > 59:
            return None
        return h * 3600 + m * 60
    except (ValueError, IndexError):
        return None


def money(amount, symbol: str = "$") -> str:
    q = int(Decimal(amount).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return f"{symbol}{q:,}"


def money_cents(amount, symbol: str = "$") -> str:
    q = Decimal(amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{symbol}{q:,.2f}"


def truncate_words(text: str, n: int = 3) -> str:
    if not text:
        return ""
    words = text.split()
    if len(words) <= n:
        return text
    return " ".join(words[:n]) + " …"
