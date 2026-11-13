"""Role filters used at router level (see handlers/__init__.py).

Authorization model
-------------------
* **admin**    – Telegram user id is listed in ``ADMIN_IDS`` (config is the source of truth;
  the ``users.role`` column is only kept in sync for display/notifications).
* **courier**  – ``users.role == 'courier'`` *and* an active row in ``couriers``.
* **customer** – everyone else.

Router-level filters stop crafted callback data from reaching a handler at all;
per-object checks (order ownership, assigned courier) live next to the handlers
and in ``db_helpers.transition_order_status``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import asyncpg
from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject, User

from core.config import Settings
from db_helpers import COURIER_ROLE, get_courier


def is_admin_user(user: User | None, settings: Settings) -> bool:
    return user is not None and settings.is_admin(user.id)


async def is_active_courier(pool: asyncpg.Pool, db_user: Mapping[str, Any] | None) -> bool:
    if not db_user or db_user.get("role") != COURIER_ROLE:
        return False
    courier = await get_courier(pool, db_user["id"])
    return bool(courier and courier["is_active"])


def is_order_owner(order: Mapping[str, Any] | None, user_id: int) -> bool:
    return bool(order) and order["user_id"] == user_id


def is_assigned_courier(order: Mapping[str, Any] | None, courier_id: int) -> bool:
    return bool(order) and order.get("courier_id") == courier_id


class IsAdmin(BaseFilter):
    """Passes only for users whose id is in ``ADMIN_IDS``."""

    async def __call__(
        self,
        event: TelegramObject,
        settings: Settings,
        event_from_user: User | None = None,
    ) -> bool:
        return is_admin_user(event_from_user, settings)


class IsCourier(BaseFilter):
    """Passes only for active couriers."""

    async def __call__(
        self,
        event: TelegramObject,
        pool: asyncpg.Pool,
        db_user: Mapping[str, Any] | None = None,
    ) -> bool:
        return await is_active_courier(pool, db_user)
