"""Dispatcher middlewares."""

from __future__ import annotations

import logging
import time
from collections import deque
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User

from core.config import Settings
from db_helpers import ensure_user

logger = logging.getLogger(__name__)


class ThrottleMiddleware(BaseMiddleware):
    """Per-user flood control: drops updates beyond ``limit`` per ``window`` seconds.

    Runs before :class:`UserMiddleware`, so a flood never reaches the database or
    the admin notification group. Admins are never throttled.
    """

    def __init__(self, limit: int = 30, window: float = 10.0, clock: Callable[[], float] = time.monotonic) -> None:
        self.limit, self.window, self.clock = limit, window, clock
        self.hits: dict[int, deque[float]] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")
        settings: Settings | None = data.get("settings")
        if user is None or (settings is not None and settings.is_admin(user.id)):
            return await handler(event, data)
        now = self.clock()
        if len(self.hits) > 50_000:  # forget idle users so the map stays bounded
            self.hits = {k: v for k, v in self.hits.items() if v and now - v[-1] < self.window}
        q = self.hits.setdefault(user.id, deque())
        while q and now - q[0] >= self.window:
            q.popleft()
        if len(q) >= self.limit:
            if len(q) == self.limit:
                logger.warning("Throttling user", extra={"user_id": user.id})
                q.append(now)
            return None
        q.append(now)
        return await handler(event, data)


class UserMiddleware(BaseMiddleware):
    """Loads (or creates) the DB user for every update and syncs the admin role.

    Puts the record into ``data["db_user"]`` so filters and handlers can use it
    without another query. Users that never sent /start (e.g. an admin clicking a
    button in the notification group) therefore always have a row.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")
        if user is not None and not user.is_bot:
            settings: Settings = data["settings"]
            data["db_user"] = await ensure_user(
                data["pool"],
                user.id,
                user.first_name,
                user.username,
                user.language_code,
                is_admin=settings.is_admin(user.id),
            )
        return await handler(event, data)
