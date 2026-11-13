# handlers/admin/menu.py
"""Admin bosh menyusi va admin tilini tanlash."""

from __future__ import annotations

import logging

import asyncpg
from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from db_helpers import get_user, set_user_selected_language
from handlers.admin.common import I18N, _lang
from locales.lexicon import LEXICON
from utils.keyboards import build_admin_main_menu
from utils.lexicon_utils import SUPPORTED_LANGUAGES, get_text

logger = logging.getLogger(__name__)
router = Router(name="admin.menu")


# ────────────────────────── ADMIN BOSH MENYUSI ────────────────────────────
@router.callback_query(F.data == "admin_main_menu")
async def cb_admin_main_menu(call: CallbackQuery, pool: asyncpg.Pool):
    user = await get_user(pool, call.from_user.id)
    lang = _lang(user)
    await call.message.edit_text(get_text("admin_welcome", lang, LEXICON), reply_markup=build_admin_main_menu(lang))
    await call.answer()


@router.callback_query(F.data == "admin_change_language")
async def cb_admin_change_language(call: CallbackQuery, pool: asyncpg.Pool):
    user = await get_user(pool, call.from_user.id)
    lang = _lang(user)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🇺🇿 O‘zbekcha", callback_data="admin_lang_select:uz")],
            [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="admin_lang_select:ru")],
            [InlineKeyboardButton(text="🇺🇸 English", callback_data="admin_lang_select:en")],
            [
                InlineKeyboardButton(
                    text=get_text("back_button", lang, I18N),
                    callback_data="restaurant_settings",
                )
            ],
        ]
    )
    await call.message.edit_text(get_text("change_language_button", lang, I18N), reply_markup=kb)
    await call.answer()


@router.callback_query(F.data.startswith("admin_lang_select:"))
async def cb_admin_lang_select(call: CallbackQuery, pool: asyncpg.Pool):
    lang_code = call.data.split(":")[1]
    if lang_code not in SUPPORTED_LANGUAGES:
        return await call.answer()
    await set_user_selected_language(pool, call.from_user.id, lang_code)
    await call.answer(get_text("language_set_alert", lang_code, I18N), show_alert=True)
    # Til o'zgargandan keyin bosh menyuni qayta ko'rsatamiz
    await cb_admin_main_menu(call, pool)
