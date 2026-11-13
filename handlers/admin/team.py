# handlers/admin/team.py
"""Jamoa (kuryerlar) boshqaruvi."""

from __future__ import annotations

import logging

import asyncpg
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from db_helpers import add_courier, get_all_couriers, get_courier, get_user, reactivate_courier, remove_courier
from handlers.admin.common import _lang, parse_int_arg
from locales.lexicon import LEXICON
from utils.keyboards import build_courier_details_menu, build_pagination_keyboard, build_team_management_menu
from utils.lexicon_utils import get_text

logger = logging.getLogger(__name__)
router = Router(name="admin.team")


# ─── Jamoa boshqaruvi menyusini ochish ────────────────────────
@router.callback_query(F.data == "manage_team")
async def cb_manage_team(call: CallbackQuery, pool: asyncpg.Pool):
    user = await get_user(pool, call.from_user.id)
    lang = _lang(user)
    await call.message.edit_text(
        get_text("team_management_title", lang, LEXICON), reply_markup=build_team_management_menu(lang)
    )
    await call.answer()


class AddCourierFSM(StatesGroup):
    waiting_for_id = State()
    waiting_for_name = State()
    waiting_for_phone = State()


COURIERS_PER_PAGE = 10


async def _courier_list_view(pool: asyncpg.Pool, lang: str, page: int = 0) -> tuple[str, InlineKeyboardMarkup]:
    """Kuryerlar ro'yxatining bitta sahifasi (matn + klaviatura)."""
    couriers = await get_all_couriers(pool)
    last_page = max(0, (len(couriers) - 1) // COURIERS_PER_PAGE)
    page = min(max(page, 0), last_page)
    chunk = couriers[page * COURIERS_PER_PAGE : (page + 1) * COURIERS_PER_PAGE]

    kb = build_pagination_keyboard(
        items_list=[(c["user_id"], c["full_name"]) for c in chunk],
        current_page=page,
        total_items=len(couriers),
        callback_prefix="courier",
        lang=lang,
        back_callback_data="manage_team",
        page_callback=lambda p: f"courier_page:{p}",
        max_items_per_page=COURIERS_PER_PAGE,
    )
    # “➕ Kuriyer qo‘shish” tugmasi sahifaning boshida
    kb.inline_keyboard.insert(
        0, [InlineKeyboardButton(text=get_text("add_courier_btn", lang, LEXICON), callback_data="add_courier")]
    )
    return get_text("courier_list_title", lang, LEXICON), kb


@router.callback_query(F.data == "manage_couriers_btn")
async def cb_manage_couriers(call: CallbackQuery, pool: asyncpg.Pool, page: int = 0):
    lang = _lang(await get_user(pool, call.from_user.id))
    title, kb = await _courier_list_view(pool, lang, page)
    await call.message.edit_text(title, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("courier_page:"))
async def cb_courier_page(call: CallbackQuery, pool: asyncpg.Pool):
    page = parse_int_arg(call.data)
    if page is None:
        return await call.answer()
    await cb_manage_couriers(call, pool, page=page)


# ─── “add_courier” callback: FSMni boshlaydi ─────────────────────────────
@router.callback_query(F.data == "add_courier")
async def cb_add_courier(call: CallbackQuery, state: FSMContext, pool: asyncpg.Pool):
    user = await get_user(pool, call.from_user.id)
    lang = _lang(user)

    await state.set_state(AddCourierFSM.waiting_for_id)
    await call.message.edit_text(get_text("ask_for_courier_id", lang, LEXICON))
    await call.answer()


# ─── Ism qabul qilish ────────────────────────────────────────────────────
@router.message(AddCourierFSM.waiting_for_name, F.text)
async def fsm_courier_name(message: Message, state: FSMContext, pool: asyncpg.Pool):  # <-- pool qo'shildi
    full_name = message.text.strip()
    await state.update_data(full_name=full_name)
    await state.set_state(AddCourierFSM.waiting_for_phone)

    # pool endi to'g'ridan-to'g'ri ishlatilmoqda
    lang = _lang(await get_user(pool, message.from_user.id))
    await message.answer(get_text("ask_for_courier_phone", lang, LEXICON))


# ─── Telefon qabul qilish yoki o‘tkazib yuborish ─────────────────────────
@router.message(AddCourierFSM.waiting_for_phone, F.text)
async def fsm_courier_phone(message: Message, state: FSMContext, pool: asyncpg.Pool):
    data = await state.get_data()
    phone_text = message.text.strip()
    # /skip buyrug'ini kichik harflarda tekshiramiz
    phone = None if phone_text.lower() == "/skip" else phone_text

    # Kuriyerni bazaga qo'shamiz
    await add_courier(
        pool=pool,
        user_id=data["user_id"],
        full_name=data["full_name"],
        phone_number=phone,  # db_helpers.py dagi parametr nomiga moslashtirildi
    )
    await state.clear()

    lang = _lang(await get_user(pool, message.from_user.id))
    await message.answer(get_text("courier_added_success", lang, LEXICON))

    # Yangilangan ro'yxatni yangi xabar sifatida yuboramiz
    title, kb = await _courier_list_view(pool, lang, 0)
    await message.answer(title, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("courier:"))
async def cb_courier_details(call: CallbackQuery, pool: asyncpg.Pool):
    """
    Admin “courier:{id}:…” tugmasini bosganda —
    tanlangan kuriyerning ism va telefonini ko‘rsatadi.
    """
    # 1) courier_id ni ajratib olamiz
    _, courier_id_str, *_ = call.data.split(":")
    courier_id = int(courier_id_str)

    # 2) Bazadan kuriyer ma'lumotlarini olamiz
    courier_rec = await get_courier(pool, courier_id)
    if not courier_rec:
        user = await get_user(pool, call.from_user.id)
        lang = _lang(user)
        return await call.answer(get_text("user_not_found_error", lang, LEXICON), show_alert=True)

    # 3) Admin tilini aniqlaymiz
    admin = await get_user(pool, call.from_user.id)
    lang = _lang(admin)

    # 4) Matnni tayyorlaymiz
    name = courier_rec["full_name"]
    phone = courier_rec["phone_number"] or ""
    text = f"{name} — {phone}"

    # 5) Tugmalarni yaratamiz
    kb = build_courier_details_menu(lang, courier_id)

    # 6) Xabarni tahrirlab chiqaramiz
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()


@router.callback_query(F.data.startswith("remove_courier:"))
async def cb_remove_courier_confirm(call: CallbackQuery, pool: asyncpg.Pool):
    """
    “remove_courier:{id}” bosilganda —
    kuriyerni o‘chirishni tasdiqlash oynasini ko‘rsatadi.
    """
    _, courier_id_str = call.data.split(":", 1)
    courier_id = int(courier_id_str)

    admin = await get_user(pool, call.from_user.id)
    lang = _lang(admin)

    # Kuriyer nomini olish
    courier_rec = await get_courier(pool, courier_id)
    name = courier_rec["full_name"] if courier_rec else ""

    # 1) Tasdiq matni
    text = get_text("confirm_courier_removal_tpl", lang, LEXICON).format(name=name, id=courier_id)

    # 2) “Yes” va “No” tugmalari
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅", callback_data=f"confirm_remove_courier:{courier_id}")],
            [
                InlineKeyboardButton(
                    text=get_text("back_button", lang, LEXICON), callback_data=f"courier:{courier_id}:0"
                )
            ],
        ]
    )

    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()


@router.callback_query(F.data.startswith("confirm_remove_courier:"))
async def cb_confirm_remove_courier(call: CallbackQuery, pool: asyncpg.Pool):
    """
    “confirm_remove_courier:{id}” bosilganda —
    kuriyerni o‘chirish va ro‘yxatni yangilash.
    """
    _, courier_id_str = call.data.split(":", 1)
    courier_id = int(courier_id_str)

    # 1) DB helper chaqiramiz
    await remove_courier(pool, courier_id)

    # 2) Muvaffaqiyat alerti
    admin = await get_user(pool, call.from_user.id)
    lang = _lang(admin)
    await call.answer(get_text("courier_removed_success", lang, LEXICON), show_alert=True)

    # 3) Kuriyerlar ro‘yxatini qayta ko‘rsatamiz
    await cb_manage_couriers(call, pool)


@router.message(AddCourierFSM.waiting_for_id, F.text)
async def fsm_courier_id(message: Message, state: FSMContext, pool: asyncpg.Pool):
    """
    Kuriyer ID sini qabul qiladi va:
      • Yangi kuriyer bo'lsa → ism so'raydi
      • Allaqachon faol kuriyer bo'lsa → xato xabar
      • Inaktiv kuriyer bo'lsa → qayta faollashtirishni tasdiqlaydi
    """
    lang = _lang(await get_user(pool, message.from_user.id))
    text = message.text.strip()

    # 1) Raqam emasa
    if not text.isdigit():
        return await message.answer(get_text("invalid_id_error", lang, LEXICON))

    user_id = int(text)

    # 2) Foydalanuvchi mavjudligini tekshir
    user_rec = await get_user(pool, user_id)
    if not user_rec:
        return await message.answer(get_text("user_not_found_error", lang, LEXICON))

    # 3) Kuriyer sifatida ro'yxatda bor-yo'qligini tekshir
    courier_rec = await get_courier(pool, user_id)
    if courier_rec:
        if courier_rec["is_active"]:
            # Allaqachon faol
            await state.clear()
            return await message.answer(get_text("user_is_already_active_courier", lang, LEXICON))
        else:
            # Inaktiv → qayta faollashtirishni so'rash
            await state.clear()
            text = get_text("confirm_courier_reactivation_tpl", lang, LEXICON).format(name=courier_rec["full_name"])
            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=get_text("confirm_continue", lang, LEXICON),
                            callback_data=f"reactivate_courier_yes:{user_id}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text=get_text("confirm_cancel", lang, LEXICON), callback_data="manage_couriers_btn"
                        )
                    ],
                ]
            )
            return await message.answer(text, reply_markup=kb)

    # 4) Yangi kuriyer → ism so'rash bosqichi
    await state.update_data(user_id=user_id)
    await state.set_state(AddCourierFSM.waiting_for_name)
    await message.answer(get_text("ask_for_courier_name", lang, LEXICON))


@router.callback_query(F.data.startswith("reactivate_courier_yes:"))
async def cb_reactivate_courier_yes(call: CallbackQuery, state: FSMContext, pool: asyncpg.Pool):
    """
    Admin “Ha” tugmasini bosganda—
    inaktiv kuriyerni qayta faollashtiradi va ro'yxatni yangilaydi.
    """
    user_id = parse_int_arg(call.data)
    courier_rec = await get_courier(pool, user_id) if user_id is not None else None
    if courier_rec is None:
        lang = _lang(await get_user(pool, call.from_user.id))
        return await call.answer(get_text("user_not_found_error", lang, LEXICON), show_alert=True)

    # 1) Qayta faollashtirish
    await reactivate_courier(pool, user_id)

    # 2) FSM holatini tozalash
    await state.clear()

    # 3) Success alert
    admin = await get_user(pool, call.from_user.id)
    lang = _lang(admin)
    await call.answer(get_text("courier_reactivated_success", lang, LEXICON), show_alert=True)

    # 4) Yangilangan kursiyerlar ro'yxatini qayta chaqirish
    await cb_manage_couriers(call, pool)
