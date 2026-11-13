# handlers/admin/settings.py
"""Kafe sozlamalari: zona, tillar, ish vaqti, bufer, bekor qilish oynasi, hisoblagich."""

from __future__ import annotations

import logging
from datetime import datetime

import asyncpg
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from db_helpers import (
    get_all_languages,
    get_cafe_settings,
    get_user,
    reset_daily_order_counter,
    toggle_language_status,
    update_cafe_location,
    update_cafe_radius,
    update_cancel_window,
    update_order_buffer,
    update_work_hours,
)
from handlers.admin.common import _lang
from locales.lexicon import LEXICON
from utils.keyboards import build_language_management_menu, build_settings_menu
from utils.lexicon_utils import get_text

logger = logging.getLogger(__name__)
router = Router(name="admin.settings")


@router.callback_query(F.data == "restaurant_settings")
async def cb_restaurant_settings(call: CallbackQuery, pool: asyncpg.Pool):
    """Admin sozlamalari menyusini ko'rsatadi."""
    user = await get_user(pool, call.from_user.id)
    lang = _lang(user)
    # `build_settings_menu` endi soddalashtirilgan
    kb = build_settings_menu(lang)
    await call.message.edit_text(get_text("settings_title", lang, LEXICON), reply_markup=kb)
    await call.answer()


# ───────── Zone boshqaruvi FSM ─────────────────
class ZoneManagementFSM(StatesGroup):
    waiting_for_location = State()
    waiting_for_radius = State()


@router.callback_query(F.data == "manage_zone")
async def cb_manage_zone(call: CallbackQuery, pool):
    user = await get_user(pool, call.from_user.id)
    lang = user.get("selected_language_code") or user.get("language_code") or "uz"

    settings = await get_cafe_settings(pool)
    lat = settings.get("latitude") or "Not set"
    lon = settings.get("longitude") or "Not set"
    rad = settings.get("delivery_radius_km") or "Not set"

    text = get_text("current_zone_info_tpl", lang, LEXICON).format(lat=lat, lon=lon, radius=rad)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=get_text("set_location_btn", lang, LEXICON), callback_data="set_location_btn")],
            [InlineKeyboardButton(text=get_text("set_radius_btn", lang, LEXICON), callback_data="set_radius_btn")],
            [InlineKeyboardButton(text=get_text("back_button", lang, LEXICON), callback_data="restaurant_settings")],
        ]
    )
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()


@router.callback_query(F.data == "set_location_btn")
async def cb_set_location(call: CallbackQuery, state: FSMContext, pool):
    user = await get_user(pool, call.from_user.id)
    lang = user.get("selected_language_code") or user.get("language_code") or "uz"

    await state.set_state(ZoneManagementFSM.waiting_for_location)
    await call.message.answer(get_text("ask_for_cafe_location", lang, LEXICON))
    await call.answer()


@router.message(ZoneManagementFSM.waiting_for_location, F.content_type == "location")
async def fsm_zone_location(message: Message, state: FSMContext, pool):
    loc = message.location
    await update_cafe_location(pool, loc.latitude, loc.longitude)
    await state.clear()

    user = await get_user(pool, message.from_user.id)
    lang = user.get("selected_language_code") or user.get("language_code") or "uz"
    await message.answer(get_text("location_updated_success", lang, LEXICON))


@router.callback_query(F.data == "set_radius_btn")
async def cb_set_radius(call: CallbackQuery, state: FSMContext, pool):
    user = await get_user(pool, call.from_user.id)
    lang = user.get("selected_language_code") or user.get("language_code") or "uz"

    await state.set_state(ZoneManagementFSM.waiting_for_radius)
    await call.message.answer(get_text("ask_for_radius_km", lang, LEXICON))
    await call.answer()


@router.message(ZoneManagementFSM.waiting_for_radius, F.text)
async def fsm_zone_radius(message: Message, state: FSMContext, pool):
    text = message.text.strip()
    user = await get_user(pool, message.from_user.id)
    lang = user.get("selected_language_code") or user.get("language_code") or "uz"

    try:
        radius = float(text.replace(",", "."))
        if not 0 < radius < 1000:  # DECIMAL(5,2) chegarasi
            raise ValueError
    except ValueError:
        await message.answer(get_text("invalid_radius_error", lang, LEXICON))
        return

    await update_cafe_radius(pool, radius)
    await state.clear()
    await message.answer(get_text("radius_updated_success", lang, LEXICON))


@router.callback_query(F.data == "manage_languages")
async def cb_manage_languages(call: CallbackQuery, pool: asyncpg.Pool):
    """Tillar ro'yxatini ko'rsatuvchi menyuni ochadi."""
    user = await get_user(pool, call.from_user.id)
    # Huquqni tekshirish

    all_langs = await get_all_languages(pool)
    lang = _lang(user)
    kb = build_language_management_menu(all_langs, lang)

    await call.message.edit_text(get_text("language_management_title", lang, LEXICON), reply_markup=kb)
    await call.answer()


@router.callback_query(F.data.startswith("toggle_lang:"))
async def cb_toggle_language(call: CallbackQuery, pool: asyncpg.Pool):
    """Tilning holatini o'zgartiradi va menyuni yangilaydi."""
    lang_code_to_toggle = call.data.split(":")[1]

    await toggle_language_status(pool, lang_code_to_toggle)

    # Menyuni yangilangan ma'lumotlar bilan qayta ko'rsatish
    await cb_manage_languages(call, pool)


@router.callback_query(F.data == "confirm_reset_daily_id")
async def cb_confirm_reset_daily_id(call: CallbackQuery, pool: asyncpg.Pool):
    """Admin hisoblagichni yangilashni tasdiqlashini so'raydi. (YANGI)"""
    user = await get_user(pool, call.from_user.id)
    lang = _lang(user)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅", callback_data="final_reset_daily_id")],
            [InlineKeyboardButton(text="❌", callback_data="restaurant_settings")],
        ]
    )

    await call.message.edit_text(get_text("confirm_reset_prompt", lang, LEXICON), reply_markup=kb)
    await call.answer()


@router.callback_query(F.data == "final_reset_daily_id")
async def cb_final_reset_daily_id(call: CallbackQuery, pool: asyncpg.Pool):
    """Hisoblagichni yangilaydi va sozlamalar menyusiga qaytaradi. (YANGI)"""
    # Bu funksiya db_helpers'da bo'lishi kerak, shuning uchun uni import qilamiz

    await reset_daily_order_counter(pool)

    user = await get_user(pool, call.from_user.id)
    lang = _lang(user)

    await call.answer(get_text("reset_success_alert", lang, LEXICON), show_alert=True)

    # Sozlamalar menyusini qayta ko'rsatish
    await cb_restaurant_settings(call, pool)


class CancelWindowFSM(StatesGroup):
    waiting_for_minutes = State()


# 3) Callback handler to start the flow:
@router.callback_query(F.data == "set_cancel_window")
async def cb_set_cancel_window(call: CallbackQuery, state: FSMContext, pool: asyncpg.Pool):
    user = await get_user(pool, call.from_user.id)
    lang = _lang(user)

    settings = await get_cafe_settings(pool)
    current = settings.get("cancel_window_minutes", "Not set")

    await state.set_state(CancelWindowFSM.waiting_for_minutes)
    await call.message.answer(get_text("ask_for_cancel_window", lang, LEXICON).format(current_minutes=current))
    await call.answer()


# 4) Message handler to receive and validate the new value:
@router.message(CancelWindowFSM.waiting_for_minutes, F.text)
async def fsm_cancel_window(message: Message, state: FSMContext, pool: asyncpg.Pool):
    user = await get_user(pool, message.from_user.id)
    lang = _lang(user)
    text = message.text.strip()

    if not text.isdigit() or int(text) <= 0:
        # Invalid input
        return await message.answer(get_text("invalid_minutes_error", lang, LEXICON))

    minutes = int(text)
    await update_cancel_window(pool, minutes)
    await state.clear()

    # Success and show settings again
    await message.answer(get_text("cancel_window_updated_success", lang, LEXICON))
    kb = build_settings_menu(lang)
    await message.answer(get_text("settings_title", lang, LEXICON), reply_markup=kb)


class SetWorkHoursFSM(StatesGroup):
    waiting_for_start_time = State()  # ochilish vaqtini kutyapmiz
    waiting_for_end_time = State()  # yopilish vaqtini kutyapmiz


@router.callback_query(F.data == "set_work_hours")
async def cb_set_work_hours(call: CallbackQuery, state: FSMContext, pool: asyncpg.Pool):
    """“Ish vaqtini belgilash” tugmasi bosilganda."""
    user = await get_user(pool, call.from_user.id)
    lang = _lang(user)
    settings = await get_cafe_settings(pool)

    # Agar hali belgilangan bo‘lmasa — not_set_label
    start = settings.get("work_hours_start") or get_text("not_set_label", lang, LEXICON)
    end = settings.get("work_hours_end") or get_text("not_set_label", lang, LEXICON)

    # Hozirgi vaqti ko‘rsatib, yangi ochilish so‘raladi
    text = get_text("ask_for_start_time_tpl", lang, LEXICON).format(start=start, end=end)
    await state.set_state(SetWorkHoursFSM.waiting_for_start_time)
    await call.message.edit_text(text)
    await call.answer()


# handlers/admin_handlers.py


@router.message(SetWorkHoursFSM.waiting_for_start_time, F.text)
async def fsm_work_start(message: Message, state: FSMContext, pool: asyncpg.Pool):
    """Ochilish vaqtini qabul qiladi va keyingi bosqichga o‘tadi."""
    text = message.text.strip()
    lang = _lang(await get_user(pool, message.from_user.id))
    try:
        # Faqat formatni tekshirish uchun vaqtinchalik obyekt yaratamiz
        datetime.strptime(text, "%H:%M").time()
    except ValueError:
        return await message.answer(get_text("invalid_time_format_error", lang, LEXICON))

    # <<< YECHIM: FSM ga 'time' obyektini emas, kiritilgan matnning o'zini saqlaymiz
    await state.update_data(start_time_str=text)

    await state.set_state(SetWorkHoursFSM.waiting_for_end_time)
    await message.answer(get_text("ask_for_end_time", lang, LEXICON))


@router.message(SetWorkHoursFSM.waiting_for_end_time, F.text)
async def fsm_work_end(message: Message, state: FSMContext, pool: asyncpg.Pool):
    """Yopilish vaqtini qabul qilib, bazaga yozadi va tugatadi."""
    text = message.text.strip()
    lang = _lang(await get_user(pool, message.from_user.id))
    try:
        # Yopilish vaqti formatini tekshiramiz
        t_end = datetime.strptime(text, "%H:%M").time()
    except ValueError:
        return await message.answer(get_text("invalid_time_format_error", lang, LEXICON))

    # <<< YECHIM: FSM dan saqlangan matnni olamiz
    data = await state.get_data()
    start_time_str = data["start_time_str"]

    # Endi, eng oxirgi bosqichda ikkala matndan ham 'time' obyektlarini yaratamiz
    t_start = datetime.strptime(start_time_str, "%H:%M").time()

    # Va bazaga yozamiz
    await update_work_hours(pool, t_start, t_end)
    await state.clear()

    # Muvaffaqiyat xabari va sozlamalar menyusini ko‘rsatamiz
    await message.answer(get_text("work_hours_updated_success", lang, LEXICON))
    kb = build_settings_menu(lang)
    await message.answer(get_text("settings_title", lang, LEXICON), reply_markup=kb)


class SetOrderBufferFSM(StatesGroup):
    waiting_for_buffer_minutes = State()  # Buyurtma bufer minute kiritilishini kutamiz


# 3) “Bufer vaqtini o‘rnatish” tugmasi bosilganda ishlaydi:
@router.callback_query(F.data == "set_order_buffer")
async def cb_set_order_buffer(call: CallbackQuery, state: FSMContext, pool: asyncpg.Pool):
    user = await get_user(pool, call.from_user.id)
    lang = _lang(user)
    settings = await get_cafe_settings(pool)
    current = settings.get("order_acceptance_buffer_minutes", "Not set")

    # FSM holatini o'rnatamiz va so‘rov matnini yuboramiz
    await state.set_state(SetOrderBufferFSM.waiting_for_buffer_minutes)
    await call.message.answer(get_text("ask_for_order_buffer_tpl", lang, LEXICON).format(current_buffer=current))
    await call.answer()


# 4) Foydalanuvchi yangi bufer minute kiritganda:
@router.message(SetOrderBufferFSM.waiting_for_buffer_minutes, F.text)
async def fsm_set_order_buffer(message: Message, state: FSMContext, pool: asyncpg.Pool):
    lang = _lang(await get_user(pool, message.from_user.id))
    text = message.text.strip()

    # Kirish validatsiyasi: musbat butun son bo‘lishi kerak
    if not text.isdigit() or int(text) <= 0:
        return await message.answer(get_text("invalid_minutes_error", lang, LEXICON))

    minutes = int(text)
    # Bazada yangilaymiz
    await update_order_buffer(pool, minutes)
    await state.clear()

    # Muvaffaqiyat xabari va yangilangan menyuni ko‘rsatamiz
    await message.answer(get_text("order_buffer_updated_success", lang, LEXICON))
    kb = build_settings_menu(lang)
    await message.answer(get_text("settings_title", lang, LEXICON), reply_markup=kb)
