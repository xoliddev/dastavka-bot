# handlers/fallback.py
"""Oxirgi router: hech bir handler qabul qilmagan callback'larga javob beradi.

Rol filtrlari (IsAdmin / IsCourier) soxta yoki ruxsatsiz callback'ni o'z
routerlariga kiritmaydi; u shu yerga tushadi, log yoziladi va foydalanuvchi
"ruxsat yo'q" alertini oladi (Telegram'da "soat" belgisi osilib qolmaydi).
"""

from __future__ import annotations

import logging

import asyncpg
from aiogram import F, Router
from aiogram.types import CallbackQuery

from core.notify import user_lang
from db_helpers import get_user
from locales.lexicon import LEXICON
from utils.lexicon_utils import get_text

logger = logging.getLogger(__name__)
router = Router(name="fallback")


@router.callback_query(F.data == "noop")
async def cb_noop(call: CallbackQuery) -> None:
    await call.answer()


@router.callback_query()
async def cb_unhandled(call: CallbackQuery, pool: asyncpg.Pool) -> None:
    logger.warning(
        "Rejected or unknown callback",
        extra={"user_id": call.from_user.id, "callback_data": call.data},
    )
    lang = user_lang(await get_user(pool, call.from_user.id))
    await call.answer(get_text("access_denied_alert", lang, LEXICON), show_alert=True)
