from datetime import date, datetime
from decimal import Decimal
from mytime import format as fmt


def test_fmt_hm_rounds_to_nearest_minute():
    assert fmt.fmt_hm(0) == "00:00"
    assert fmt.fmt_hm(29) == "00:00"
    assert fmt.fmt_hm(30) == "00:01"
    assert fmt.fmt_hm(59) == "00:01"
    assert fmt.fmt_hm(60) == "00:01"
    assert fmt.fmt_hm(5 * 3600 + 42 * 60 + 30) == "05:43"
    assert fmt.fmt_hm(5 * 3600 + 42 * 60 + 29) == "05:42"


def test_fmt_hms():
    assert fmt.fmt_hms(0) == "0:00:00"
    assert fmt.fmt_hms(5 * 3600 + 42 * 60 + 13) == "5:42:13"


def test_parse_hm():
    assert fmt.parse_hm(1, 30) == 5400
    assert fmt.parse_hm(0, 0) == 0


def test_money():
    assert fmt.money(Decimal("1234.5")) == "$1,235"
    assert fmt.money(Decimal("0")) == "$0"
    assert fmt.money(Decimal("99.4"), "£") == "£99"
    assert fmt.money(Decimal("99.5"), "£") == "£100"


def test_fmt_date():
    assert fmt.fmt_date(date(2026, 6, 25)) == "25-06-2026"
    assert fmt.fmt_date(datetime(2026, 6, 25, 14, 30, 0)) == "25-06-2026"


def test_fmt_time():
    assert fmt.fmt_time(datetime(2026, 6, 25, 9, 5, 0)) == "09:05"
    assert fmt.fmt_time(None) == ""


def test_parse_duration():
    assert fmt.parse_duration("1:30") == 5400
    assert fmt.parse_duration("01:30") == 5400
    assert fmt.parse_duration("0:00") == 0
    assert fmt.parse_duration("00:00") == 0
    assert fmt.parse_duration("2:45") == 2 * 3600 + 45 * 60
    assert fmt.parse_duration("invalid") is None   # non-numeric returns None
    assert fmt.parse_duration("") == 0
    assert fmt.parse_duration("1:60") is None       # invalid minutes returns None
    assert fmt.parse_duration("2") == 7200          # plain hours
    assert fmt.parse_duration("0") == 0
    assert fmt.parse_duration("3:66") is None       # minutes > 59 returns None
