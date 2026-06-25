from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session

from mytime.models import Settings


def get_settings(session: Session) -> Settings:
    s = session.scalars(select(Settings).limit(1)).first()
    if s is None:
        s = Settings(default_hourly_rate=Decimal("0"), currency_symbol="$", invoice_prefix="INV-")
        session.add(s)
        session.commit()
    return s


def update_settings(
    session: Session,
    default_hourly_rate: Decimal,
    currency_symbol: str,
    invoice_prefix: str = "INV-",
) -> Settings:
    s = get_settings(session)
    s.default_hourly_rate = Decimal(default_hourly_rate)
    s.currency_symbol = currency_symbol
    s.invoice_prefix = invoice_prefix
    session.commit()
    return s
