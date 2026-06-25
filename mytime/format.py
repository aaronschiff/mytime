from decimal import Decimal, ROUND_HALF_UP


def fmt_hm(seconds: int) -> str:
    minutes = seconds // 60
    return f"{minutes // 60}h {minutes % 60}m"


def fmt_hms(seconds: int) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}"


def parse_hm(hours: int, minutes: int) -> int:
    return int(hours) * 3600 + int(minutes) * 60


def money(amount, symbol: str = "$") -> str:
    q = Decimal(amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{symbol}{q:,.2f}"
