from decimal import Decimal
from mytime import format as fmt


def test_fmt_hm_rounds_to_minutes():
    assert fmt.fmt_hm(0) == "0h 0m"
    assert fmt.fmt_hm(5 * 3600 + 42 * 60 + 30) == "5h 42m"
    assert fmt.fmt_hm(59) == "0h 0m"
    assert fmt.fmt_hm(60) == "0h 1m"


def test_fmt_hms():
    assert fmt.fmt_hms(0) == "0:00:00"
    assert fmt.fmt_hms(5 * 3600 + 42 * 60 + 13) == "5:42:13"


def test_parse_hm():
    assert fmt.parse_hm(1, 30) == 5400
    assert fmt.parse_hm(0, 0) == 0


def test_money():
    assert fmt.money(Decimal("1234.5")) == "$1,234.50"
    assert fmt.money(Decimal("0")) == "$0.00"
    assert fmt.money(Decimal("99.999"), "£") == "£100.00"
