"""Dispatcher middlewares."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User

from core.config import Settings
from db_helpers import ensure_user

logger = logging.getLogger(__name__)


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
