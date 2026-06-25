from decimal import Decimal
from mytime.services import settings_service as svc


def test_get_settings_creates_default_row(session):
    s = svc.get_settings(session)
    assert s.currency_symbol == "$"
    assert s.default_hourly_rate == Decimal("0")
    # idempotent — same row returned, not a second one
    again = svc.get_settings(session)
    assert again.id == s.id


def test_update_settings(session):
    svc.get_settings(session)
    s = svc.update_settings(session, Decimal("175.00"), "£")
    assert s.default_hourly_rate == Decimal("175.00")
    assert s.currency_symbol == "£"
