# handlers/admin/group.py
"""/set_group buyrug'i (xabarnoma guruhini sozlash bo'yicha yo'riqnoma)."""

from __future__ import annotations

import logging

import asyncpg
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from core.config import Settings
from db_helpers import get_user
from handlers.admin.common import _lang
from locales.lexicon import LEXICON
from utils.lexicon_utils import get_text

logger = logging.getLogger(__name__)
router = Router(name="admin.group")


@router.message(Command("set_group"))
async def cmd_set_group(message: Message, pool: asyncpg.Pool, settings: Settings):
    """Xabarnoma guruhini .env fayli orqali sozlash uchun yo'riqnoma.

    Bu router ``IsAdmin`` filtridan tashqarida: admin bo'lmaganlarga tushuntirish beriladi.
    """
    if message.chat.type not in ("group", "supergroup"):
        await message.answer(get_text("not_a_group_error", "uz", LEXICON))
        return

    if not settings.is_admin(message.from_user.id if message.from_user else None):
        lang = _lang(await get_user(pool, message.from_user.id))
        await message.answer(get_text("must_be_admin_error", lang, LEXICON))
        return

    chat_id = message.chat.id
    instruction_text = (
        "✅ Guruh ro'yxatga olindi!\n\n"
        "Bot yangi buyurtmalar haqidagi xabarnomalarni shu guruhga yuborishi uchun, "
        "loyihangizdagi `.env` fayliga quyidagi qatorni qo'shing va botni qayta ishga tushiring:\n\n"
        f"`NOTIFICATION_GROUP_ID={chat_id}`"
    )

    await message.answer(instruction_text, parse_mode="Markdown")
