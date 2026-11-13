"""Opening-hours logic, timezone-aware and safe for shifts that cross midnight."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, tzinfo


def _shift_bounds(day: date, start: time, end: time, tz: tzinfo) -> tuple[datetime, datetime]:
    """Opening and closing moments of the shift that *starts* on ``day``."""
    opens = datetime.combine(day, start, tzinfo=tz)
    close_day = day if end > start else day + timedelta(days=1)
    closes = datetime.combine(close_day, end, tzinfo=tz)
    return opens, closes


def is_accepting_orders(
    now: datetime,
    start: time | None,
    end: time | None,
    buffer_minutes: int = 0,
    tz: tzinfo | None = None,
) -> bool:
    """Return True if an order placed at ``now`` should be accepted.

    * ``start``/``end`` are local wall-clock times; if either is missing the cafe
      is considered always open.
    * ``end <= start`` means the shift crosses midnight (e.g. 18:00 → 03:00).
      ``start == end`` is treated as a 24-hour shift.
    * Orders stop ``buffer_minutes`` before closing time.
    """
    if start is None or end is None:
        return True
    if now.tzinfo is None:
        raise ValueError("`now` must be timezone-aware")
    tz = tz or now.tzinfo
    local_now = now.astimezone(tz)
    buffer = timedelta(minutes=max(buffer_minutes or 0, 0))

    # The shift that is currently running started either today or yesterday.
    for day in (local_now.date(), local_now.date() - timedelta(days=1)):
        opens, closes = _shift_bounds(day, start, end, tz)
        if opens <= local_now < closes - buffer:
            return True
    return False


def local_day_bounds(day: date, tz: tzinfo) -> tuple[datetime, datetime]:
    """[start, end) of a calendar day in the given timezone, as aware datetimes."""
    start = datetime.combine(day, time.min, tzinfo=tz)
    end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=tz)
    return start, end
