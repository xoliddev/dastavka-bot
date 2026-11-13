# handlers/admin/variations.py
"""Mahsulot variantlarini boshqarish."""

from __future__ import annotations

import json
import logging

import asyncpg
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from db_helpers import (
    add_product_variation,
    delete_variation,
    get_enabled_languages,
    get_product_variations,
    get_user,
    get_variation_details_with_product_name,
    toggle_variation_availability,
    update_variation_name,
    update_variation_photo,
    update_variation_price,
)
from handlers.admin.common import I18N, _lang
from locales.lexicon import LEXICON
from utils.keyboards import build_single_variation_menu, build_variation_list_keyboard
from utils.lexicon_utils import get_text

logger = logging.getLogger(__name__)
router = Router(name="admin.variations")


@router.callback_query(F.data.startswith("manage_variations:"))
async def cb_manage_variations(call: CallbackQuery, pool: asyncpg.Pool):
    """
    “manage_variations:{product_id}” tugmasini bosishni qayta ishlaydi.
    Vazifasi - product_id ni aniqlab, asosiy chizuvchi funksiyani chaqirish.
    """
    product_id = int(call.data.split(":", 1)[1])
    await show_variation_list(call, pool, product_id)


class AddVariationFSM(StatesGroup):
    waiting_for_name = State()  # nomni so‘raymiz
    waiting_for_photo = State()  # yangi: rasmni so‘raymiz
    waiting_for_price = State()  # narxni so‘raymiz


@router.callback_query(F.data.startswith("add_variation:"))
async def cb_add_variation(call: CallbackQuery, state: FSMContext, pool: asyncpg.Pool):
    product_id = int(call.data.split(":", 1)[1])
    langs_recs = await get_enabled_languages(pool)
    if not langs_recs:
        lang = _lang(await get_user(pool, call.from_user.id))
        await call.answer(get_text("no_enabled_languages_error", lang, LEXICON), show_alert=True)
        return
    langs = [r["code"] for r in langs_recs]

    await state.set_state(AddVariationFSM.waiting_for_name)
    await state.update_data(product_id=product_id, langs=langs, idx=0, names={})

    lang = _lang(await get_user(pool, call.from_user.id))
    tpl = get_text("ask_for_variation_name_tpl", lang, I18N)
    await call.message.edit_text(tpl.format(lang=langs[0].upper()))
    await call.answer()


@router.message(AddVariationFSM.waiting_for_name, F.text)
async def fsm_variation_name(message: Message, state: FSMContext, pool: asyncpg.Pool):
    data = await state.get_data()
    langs, idx, names = data["langs"], data["idx"], data["names"]
    names[langs[idx]] = message.text.strip()
    idx += 1

    lang = _lang(await get_user(pool, message.from_user.id))
    if idx < len(langs):
        await state.update_data(idx=idx, names=names)
        tpl = get_text("ask_for_variation_name_tpl", lang, I18N)
        await message.answer(tpl.format(lang=langs[idx].upper()))
    else:
        # barcha nomlar to‘plandi → rasm so‘raymiz
        await state.update_data(names=names)
        await state.set_state(AddVariationFSM.waiting_for_photo)
        # yangi lexicon kaliti
        await message.answer(get_text("ask_for_variation_photo", lang, I18N))


@router.message(AddVariationFSM.waiting_for_photo, F.photo)
async def fsm_variation_photo(message: Message, state: FSMContext, pool: asyncpg.Pool):
    # foydalanuvchi rasm yubordi
    file_id = message.photo[-1].file_id
    await state.update_data(photo_file_id=file_id)

    lang = _lang(await get_user(pool, message.from_user.id))
    await state.set_state(AddVariationFSM.waiting_for_price)
    await message.answer(get_text("ask_for_variation_price", lang, I18N))


@router.message(AddVariationFSM.waiting_for_photo, F.text == "/skip")
async def fsm_variation_skip_photo(message: Message, state: FSMContext, pool: asyncpg.Pool):
    # foydalanuvchi rasm yuborishni o‘tkazib yubordi
    await state.update_data(photo_file_id=None)

    lang = _lang(await get_user(pool, message.from_user.id))
    await state.set_state(AddVariationFSM.waiting_for_price)
    await message.answer(get_text("ask_for_variation_price", lang, I18N))


@router.message(AddVariationFSM.waiting_for_price, F.text)
async def fsm_variation_price(message: Message, state: FSMContext, pool: asyncpg.Pool):
    lang = _lang(await get_user(pool, message.from_user.id))
    try:
        price = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer(get_text("price_only_number", lang, I18N))
        return

    data = await state.get_data()
    # endi photo_file_id ni ham uzatamiz
    await add_product_variation(
        pool=pool,
        product_id=data["product_id"],
        name_jsonb=data["names"],
        price=price,
        photo_file_id=data.get("photo_file_id"),
    )
    await state.clear()

    await message.answer(get_text("variation_added_success", lang, I18N))
    await show_variation_list(message, pool, data["product_id"])


async def show_variation_list(target: Message | CallbackQuery, pool: asyncpg.Pool, product_id: int):
    """
    Mahsulot variantlari ro'yxatini ko'rsatadigan markaziy funksiya.
    Bu endi xabar turiga (rasmli yoki matnli) bog'liq emas.
    """
    user = await get_user(pool, target.from_user.id)
    lang = _lang(user)

    # Variantlarni olish va klaviaturani qurish
    variations = await get_product_variations(pool, product_id)
    kb = build_variation_list_keyboard(variations, product_id, lang)

    # Matnni tayyorlash
    title = get_text("variation_list_title", lang, LEXICON)
    text = title
    if not variations:
        text += "\n\n" + get_text("no_variations_yet", lang, LEXICON)

    # Xabarni yuborish
    if isinstance(target, CallbackQuery):
        # Agar tugma bosilgan bo'lsa, eski xabarni o'chirib, yangisini yuboramiz
        # Bu 'no text to edit' xatosini chetlab o'tadi
        await target.message.delete()
        await target.message.answer(text, reply_markup=kb)
        await target.answer()
    else:  # Message
        # Agar FSMdan keyin chaqirilsa, shunchaki yangi xabar yuboramiz
        await target.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("view_variation:"))
async def cb_view_variation(call: CallbackQuery, pool: asyncpg.Pool):
    """Tugma bosilishini qabul qilib, markaziy funksiyaga uzatadi."""
    variation_id = int(call.data.split(":", 1)[1])
    await show_single_variation_view(call, pool, variation_id)


@router.callback_query(F.data.startswith("toggle_variation_availability:"))
async def cb_toggle_variation_availability(call: CallbackQuery, pool):
    """
    Variatsiya mavjudligini almashtiradi va ko'rinishni yangilaydi.
    """
    var_id = int(call.data.split(":", 1)[1])
    await toggle_variation_availability(pool, var_id)
    # Ko'rinishni yangilash
    await cb_view_variation(call, pool)


# handlers/admin_handlers.py


@router.callback_query(F.data.startswith("confirm_delete_variation:"))
async def cb_confirm_delete_variation(call: CallbackQuery, pool):
    """
    O'chirishni tasdiqlash oynasini ko'rsatadi (BARQAROR VERSIYA).
    """
    var_id = int(call.data.split(":", 1)[1])
    rec = await get_variation_details_with_product_name(pool, var_id)
    lang = _lang(await get_user(pool, call.from_user.id))
    if not rec:
        await call.answer(get_text("product_not_found", lang, I18N), show_alert=True)
        return

    names = rec["variation_name"] if isinstance(rec["variation_name"], dict) else json.loads(rec["variation_name"])
    display_name = names.get(lang) or next(iter(names.values()))

    text = get_text("confirm_variation_delete_tpl", lang, I18N).format(name=display_name)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Ha", callback_data=f"final_delete_variation:{var_id}")],
            [InlineKeyboardButton(text=get_text("back_button", lang, I18N), callback_data=f"view_variation:{var_id}")],
        ]
    )

    # <<< TUZATISH: Xabar turidan qat'iy nazar ishlashi uchun,
    # eski xabarni tahrirlash o'rniga, yangi xabar yuboramiz.
    await call.message.delete()
    await call.message.answer(text, reply_markup=kb)
    await call.answer()


@router.callback_query(F.data.startswith("final_delete_variation:"))
async def cb_final_delete_variation(call: CallbackQuery, pool):
    """
    Variatsiyani o'chiradi va ro'yxatni yangilaydi.
    """
    var_id = int(call.data.split(":", 1)[1])
    rec = await get_variation_details_with_product_name(pool, var_id)
    if not rec:
        lang = _lang(await get_user(pool, call.from_user.id))
        await call.answer(get_text("product_not_found", lang, I18N), show_alert=True)
        return

    # O'chirish
    await delete_variation(pool, var_id)

    lang = _lang(await get_user(pool, call.from_user.id))
    await call.answer(get_text("variation_deleted_success", lang, I18N), show_alert=True)

    # Asosiy ro'yxatga qaytish
    product_id = rec["product_id"]
    await show_variation_list(call, pool, product_id)


class EditVariationPriceFSM(StatesGroup):
    waiting_for_price = State()


@router.callback_query(F.data.startswith("edit_variation_price:"))
async def cb_edit_variation_price(call: CallbackQuery, state: FSMContext, pool: asyncpg.Pool):
    """
    “edit_variation_price:{id}” tugmasi bosilganda chaqiriladi:
    variatsiya ID sini saqlaydi va yangi narxni so'raydi.
    """
    variation_id = int(call.data.split(":", 1)[1])
    lang = _lang(await get_user(pool, call.from_user.id))

    await state.set_state(EditVariationPriceFSM.waiting_for_price)
    await state.update_data(variation_id=variation_id)

    # Yangi lexicon kaliti
    await call.message.answer(get_text("ask_for_new_variation_price", lang, I18N))
    await call.answer()


@router.message(EditVariationPriceFSM.waiting_for_price, F.text)
async def fsm_update_variation_price(message: Message, state: FSMContext, pool: asyncpg.Pool):
    """
    Yangi narxni qabul qiladi va ko'rinishni markaziy funksiya orqali yangilaydi.
    """
    lang = _lang(await get_user(pool, message.from_user.id))
    try:
        new_price = float(message.text.replace(",", "."))
    except ValueError:
        return await message.answer(get_text("price_only_number", lang, I18N))

    data = await state.get_data()
    variation_id = data["variation_id"]
    await update_variation_price(pool, variation_id, new_price)

    await state.clear()

    # Muvaffaqiyat xabari
    await message.answer(get_text("variation_price_updated", lang, I18N))

    # <<< TUZATISH: Endi markaziy funksiyani to'g'ri chaqiramiz
    await show_single_variation_view(message, pool, variation_id)


# handlers/admin_handlers.py


async def show_single_variation_view(target: Message | CallbackQuery, pool: asyncpg.Pool, variation_id: int):
    """
    Bitta variantning batafsil ko'rinishini (rasm, nom, narx, tugmalar)
    chizib beradigan markaziy funksiya.
    """
    rec = await get_variation_details_with_product_name(pool, variation_id)
    user = await get_user(pool, target.from_user.id)
    lang = _lang(user)
    if not rec:
        await target.answer(get_text("product_not_found", lang, I18N), show_alert=True)
        return

    names = rec["variation_name"] if isinstance(rec["variation_name"], dict) else json.loads(rec["variation_name"])
    display_name = names.get(lang) or next(iter(names.values()))

    caption = f"<b>{display_name}</b>\nNarx: <code>{rec['price']}</code>"

    photo_id = rec["photo_file_id"]
    kb = build_single_variation_menu(rec, lang)

    # Eski xabarni o'chirib, yangisini jo'natamiz
    # Bu usul xabar turidan (rasmli/matnli) qat'iy nazar barqaror ishlaydi
    if isinstance(target, CallbackQuery):
        await target.message.delete()
        target_message = target.message
    else:  # Message
        target_message = target

    if photo_id:
        await target_message.answer_photo(photo_id, caption=caption, parse_mode="HTML", reply_markup=kb)
    else:
        # Agar variantning o'zining rasmi bo'lmasa, matnli xabar yuboramiz
        await target_message.answer(caption, parse_mode="HTML", reply_markup=kb)

    if isinstance(target, CallbackQuery):
        await target.answer()


# 1) FSM klassi
class EditVariationNameFSM(StatesGroup):
    waiting_for_name = State()


# 2) Callback: “✏️ Nomini tahrirlash” bosilganda
@router.callback_query(F.data.startswith("edit_variation_name:"))
async def cb_edit_variation_name(call: CallbackQuery, state: FSMContext, pool: asyncpg.Pool):
    variation_id = int(call.data.split(":", 1)[1])
    # Til ro‘yxatini olish
    enabled = await get_enabled_languages(pool)
    langs = [r["code"] for r in enabled] if enabled else []
    lang = _lang(await get_user(pool, call.from_user.id))

    if not langs:
        await call.answer(get_text("no_enabled_languages_error", lang, LEXICON), show_alert=True)
        return

    # FSM boshlash
    await state.set_state(EditVariationNameFSM.waiting_for_name)
    await state.update_data(variation_id=variation_id, langs=langs, idx=0, names={})
    # Birinchi til uchun so‘rash
    tpl = get_text("ask_for_new_variation_name_tpl", lang, LEXICON)
    await call.message.answer(tpl.format(lang=langs[0].upper()))
    await call.answer()


# 3) FSM: nomlarni qabul qilish
@router.message(EditVariationNameFSM.waiting_for_name, F.text)
async def fsm_edit_variation_name(message: Message, state: FSMContext, pool: asyncpg.Pool):
    data = await state.get_data()
    langs, idx, names = data["langs"], data["idx"], data["names"]
    names[langs[idx]] = message.text.strip()
    idx += 1
    # Keyingi bosqich yoki yakun
    lang = _lang(await get_user(pool, message.from_user.id))
    if idx < len(langs):
        await state.update_data(idx=idx, names=names)
        tpl = get_text("ask_for_new_variation_name_tpl", lang, LEXICON)
        await message.answer(tpl.format(lang=langs[idx].upper()))
        return

    # Hammasi to‘plandi → DB yangilash
    await update_variation_name(pool, data["variation_id"], names)
    await state.clear()

    # Muvaffaqiyat alerti va ko‘rinishni yangilash
    await message.answer(get_text("variation_name_updated", lang, LEXICON))
    await show_single_variation_view(message, pool, data["variation_id"])


# — Yangi FSM klassi —
class EditVariationPhotoFSM(StatesGroup):
    waiting_for_photo = State()


# — “Rasmni tahrirlash” tugmasi bosilganda FSMni boshlaydigan handler —
@router.callback_query(F.data.startswith("edit_variation_photo:"))
async def cb_edit_variation_photo(call: CallbackQuery, state: FSMContext, pool: asyncpg.Pool):
    variation_id = int(call.data.split(":", 1)[1])
    lang = _lang(await get_user(pool, call.from_user.id))

    await state.set_state(EditVariationPhotoFSM.waiting_for_photo)
    await state.update_data(variation_id=variation_id)
    # Yangi lexicon kaliti bilan so‘raymiz
    await call.message.answer(get_text("ask_for_new_variation_photo", lang, LEXICON))
    await call.answer()


# — Agar rasm yuborilsa: yangisini bazaga yozadi —
@router.message(EditVariationPhotoFSM.waiting_for_photo, F.photo)
async def fsm_update_variation_photo(message: Message, state: FSMContext, pool: asyncpg.Pool):
    data = await state.get_data()
    variation_id = data["variation_id"]
    new_file_id = message.photo[-1].file_id

    # db_helpers’dagi yangi funksiya
    await update_variation_photo(pool, variation_id, new_file_id)

    lang = _lang(await get_user(pool, message.from_user.id))
    await state.clear()
    # Yangi lexicon kaliti bilan muvaffaqiyat xabari
    await message.answer(get_text("variation_photo_updated", lang, LEXICON))
    # Ko‘rinishni yangilaymiz
    await show_single_variation_view(message, pool, variation_id)


# — Agar /remove komandasi yuborilsa: rasmni o‘chiradi —
@router.message(EditVariationPhotoFSM.waiting_for_photo, F.text == "/remove")
async def fsm_remove_variation_photo(message: Message, state: FSMContext, pool: asyncpg.Pool):
    data = await state.get_data()
    variation_id = data["variation_id"]

    # rasmni olib tashlaymiz (None)
    await update_variation_photo(pool, variation_id, None)

    lang = _lang(await get_user(pool, message.from_user.id))
    await state.clear()
    await message.answer(get_text("variation_photo_updated", lang, LEXICON))
    await show_single_variation_view(message, pool, variation_id)
