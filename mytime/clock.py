from datetime import datetime, date


def now() -> datetime:
    return datetime.now()


def today() -> date:
    return date.today()
