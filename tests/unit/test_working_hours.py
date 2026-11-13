from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

import pytest

from utils.working_hours import is_accepting_orders, local_day_bounds

TZ = ZoneInfo("Asia/Tashkent")  # UTC+5, no DST


def at(hour: int, minute: int = 0, day: int = 13) -> datetime:
    return datetime(2026, 11, day, hour, minute, tzinfo=TZ)


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        (at(8, 59), False),
        (at(9, 0), True),  # opening time is inclusive
        (at(12, 0), True),
        (at(21, 44), True),
        (at(21, 45), False),  # 15-minute buffer before 22:00
        (at(22, 0), False),
        (at(23, 30), False),
        (at(3, 0), False),
    ],
)
def test_regular_day_shift(now, expected):
    assert is_accepting_orders(now, time(9), time(22), buffer_minutes=15, tz=TZ) is expected


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        (at(17, 59), False),
        (at(18, 0), True),
        (at(23, 59), True),
        (at(0, 0), True),  # after midnight still belongs to yesterday's shift
        (at(1, 30), True),
        (at(2, 29), True),
        (at(2, 30), False),  # 03:00 close minus 30 min buffer
        (at(3, 0), False),
        (at(10, 0), False),
    ],
)
def test_shift_crossing_midnight(now, expected):
    assert is_accepting_orders(now, time(18), time(3), buffer_minutes=30, tz=TZ) is expected


def test_buffer_can_push_last_order_before_midnight():
    # Open 20:00 → 00:30 with a 45 min buffer: last order at 23:44.
    assert is_accepting_orders(at(23, 44), time(20), time(0, 30), 45, TZ)
    assert not is_accepting_orders(at(23, 45), time(20), time(0, 30), 45, TZ)
    assert not is_accepting_orders(at(0, 10), time(20), time(0, 30), 45, TZ)


def test_closing_exactly_at_midnight():
    assert is_accepting_orders(at(23, 59), time(10), time(0), 0, TZ)
    assert not is_accepting_orders(at(0, 0), time(10), time(0), 0, TZ)
    assert not is_accepting_orders(at(9, 59), time(10), time(0), 0, TZ)


def test_equal_start_and_end_means_24h():
    for hour in (0, 6, 12, 18, 23):
        assert is_accepting_orders(at(hour), time(8), time(8), 0, TZ)


def test_missing_hours_means_always_open():
    assert is_accepting_orders(at(4), None, time(22), 15, TZ)
    assert is_accepting_orders(at(4), time(9), None, 15, TZ)


def test_utc_input_is_converted_to_cafe_timezone():
    # 04:30 UTC == 09:30 in Tashkent → open; the old fixed-offset code relied on this too.
    now_utc = datetime(2026, 11, 13, 4, 30, tzinfo=UTC)
    assert is_accepting_orders(now_utc, time(9), time(22), 0, TZ)
    # 18:30 UTC == 23:30 local → closed for a 09-22 cafe even though it is "daytime" in UTC terms.
    assert not is_accepting_orders(datetime(2026, 11, 13, 18, 30, tzinfo=UTC), time(9), time(22), 0, TZ)


def test_dst_timezone_is_supported():
    berlin = ZoneInfo("Europe/Berlin")
    # Summer (UTC+2): 07:30 UTC is 09:30 local.
    assert is_accepting_orders(datetime(2026, 7, 1, 7, 30, tzinfo=UTC), time(9), time(18), 0, berlin)
    # Winter (UTC+1): 07:30 UTC is 08:30 local → still closed.
    assert not is_accepting_orders(datetime(2026, 1, 15, 7, 30, tzinfo=UTC), time(9), time(18), 0, berlin)


def test_naive_datetime_is_rejected():
    with pytest.raises(ValueError):
        is_accepting_orders(datetime(2026, 1, 1, 12), time(9), time(18))


def test_local_day_bounds():
    start, end = local_day_bounds(date(2026, 11, 13), TZ)
    assert start == datetime(2026, 11, 12, 19, 0, tzinfo=UTC)
    assert end == datetime(2026, 11, 13, 19, 0, tzinfo=UTC)
