"""Notifications to staff (admins in DM + optional notification group)."""

from __future__ import annotations

import logging
from collections.abc import Callable

import asyncpg
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup

from core.config import Settings
from db_helpers import get_order_receivers

logger = logging.getLogger(__name__)

# Builds (text, keyboard) for a given language code.
MessageFactory = Callable[[str], tuple[str, InlineKeyboardMarkup | None]]


def user_lang(user) -> str:
    if not user:
        return "uz"
    return user.get("selected_language_code") or user.get("language_code") or "uz"


async def notify_staff(
    bot: Bot,
    pool: asyncpg.Pool,
    settings: Settings,
    build: MessageFactory,
    **send_kwargs,
) -> None:
    """Send a message to every admin (in their language) and to the notification group."""
    receivers = await get_order_receivers(pool, settings.admin_ids)
    for receiver in receivers:
        text, kb = build(user_lang(receiver))
        try:
            await bot.send_message(receiver["id"], text, reply_markup=kb, **send_kwargs)
        except Exception:
            logger.warning("Failed to notify admin", extra={"admin_id": receiver["id"]}, exc_info=True)

    if settings.notification_group_id:
        group_lang = user_lang(receivers[0]) if receivers else "uz"
        text, kb = build(group_lang)
        try:
            await bot.send_message(settings.notification_group_id, text, reply_markup=kb, **send_kwargs)
        except Exception:
            logger.warning("Failed to notify group", extra={"group_id": settings.notification_group_id}, exc_info=True)
