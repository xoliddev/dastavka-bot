"""Flood control: a single user cannot push unlimited updates through the bot."""

from aiogram.types import User

from core.config import Settings
from core.middlewares import ThrottleMiddleware


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


async def _run(mw: ThrottleMiddleware, user_id: int, settings: Settings, times: int) -> int:
    handled = 0

    async def handler(event, data):
        nonlocal handled
        handled += 1

    for _ in range(times):
        await mw(
            handler, object(), {"event_from_user": User(id=user_id, is_bot=False, first_name="T"), "settings": settings}
        )
    return handled


async def test_drops_updates_over_the_limit_and_recovers():
    clock, cfg = Clock(), Settings(_env_file=None, admin_ids="10")
    mw = ThrottleMiddleware(limit=5, window=10, clock=clock)
    assert await _run(mw, 7, cfg, 8) == 5
    clock.now = 10.5
    assert await _run(mw, 7, cfg, 3) == 3


async def test_users_are_counted_separately_and_admins_never_throttled():
    clock, cfg = Clock(), Settings(_env_file=None, admin_ids="10")
    mw = ThrottleMiddleware(limit=2, window=10, clock=clock)
    assert await _run(mw, 7, cfg, 5) == 2
    assert await _run(mw, 8, cfg, 2) == 2
    assert await _run(mw, 10, cfg, 50) == 50
