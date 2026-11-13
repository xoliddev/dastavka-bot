# handlers/admin/products.py
"""Mahsulotlarni boshqarish (qo'shish, nom/narx/rasm/tavsif, mavjudlik, arxivlash)."""

from __future__ import annotations

import json
import logging

import asyncpg
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from db_helpers import (
    add_product,
    archive_product,
    get_enabled_languages,
    get_product,
    get_user,
    toggle_product_availability,
    update_product_description,
    update_product_name,
    update_product_photo,
    update_product_price,
)
from handlers.admin.categories import display_category_content
from handlers.admin.common import I18N, _lang, _prod_name
from locales.lexicon import LEXICON
from utils.lexicon_utils import get_text

logger = logging.getLogger(__name__)
router = Router(name="admin.products")


# ────────────────── 3-BOB: MAHSULOT QO‘SHISH FSM ────────────────────────
class AddProductFSM(StatesGroup):
    name = State()
    photo = State()
    desc = State()
    price = State()


@router.callback_query(F.data.startswith("add_product:"))
async def cb_add_product(call: CallbackQuery, state: FSMContext, pool: asyncpg.Pool):
    cat_id = int(call.data.split(":")[1])
    user = await get_user(pool, call.from_user.id)
    lang = _lang(user)

    enabled_langs_records = await get_enabled_languages(pool)
    if not enabled_langs_records:
        # TUZATILDI: Xato xabari endi LEXICON'dan olinmoqda.
        await call.message.answer(get_text("no_enabled_languages_error", lang, LEXICON))
        await call.answer()
        return

    langs = [rec["code"] for rec in enabled_langs_records]

    await state.set_state(AddProductFSM.name)
    await state.update_data(cat_id=cat_id, langs=langs, idx=0, names={}, descs={})
    prompt = get_text("ask_for_product_name_tpl", lang, I18N).format(lang=langs[0].upper())
    await call.message.answer(prompt)
    await call.answer()


@router.message(AddProductFSM.name, F.text)
async def fsm_prod_name(message: Message, state: FSMContext, pool: asyncpg.Pool):
    data = await state.get_data()
    langs, idx, names = data["langs"], data["idx"], data["names"]
    names[langs[idx]] = message.text.strip()
    idx += 1
    lang = _lang(await get_user(pool, message.from_user.id))

    if idx < len(langs):
        await state.update_data(idx=idx, names=names)
        prompt = get_text("ask_for_product_name_tpl", lang, I18N).format(lang=langs[idx].upper())
        await message.answer(prompt)
    else:
        await state.update_data(names=names)
        await state.set_state(AddProductFSM.photo)
        await message.answer(get_text("ask_for_product_photo", lang, I18N))


@router.message(AddProductFSM.photo, F.photo)
async def fsm_prod_photo(message: Message, state: FSMContext, pool: asyncpg.Pool):
    await state.update_data(photo=message.photo[-1].file_id, idx=0)
    data = await state.get_data()
    langs = data["langs"]
    lang = _lang(await get_user(pool, message.from_user.id))

    await state.set_state(AddProductFSM.desc)
    prompt = get_text("ask_for_product_desc_tpl", lang, I18N).format(lang=langs[0].upper())
    await message.answer(prompt)


@router.message(AddProductFSM.photo)
async def fsm_photo_expected(message: Message, pool: asyncpg.Pool):
    lang = _lang(await get_user(pool, message.from_user.id))
    await message.answer(get_text("no_photo_warning", lang, I18N))


@router.message(AddProductFSM.desc, F.text == "⏭️")
async def fsm_skip_desc(message: Message, state: FSMContext, pool: asyncpg.Pool):
    await state.update_data(descs={})
    await state.set_state(AddProductFSM.price)
    lang = _lang(await get_user(pool, message.from_user.id))
    await message.answer(get_text("ask_for_price", lang, I18N))


@router.message(AddProductFSM.desc, F.text)
async def fsm_prod_desc(message: Message, state: FSMContext, pool: asyncpg.Pool):
    data = await state.get_data()
    langs, idx, descs = data["langs"], data["idx"], data["descs"]
    descs[langs[idx]] = message.text.strip()
    idx += 1
    lang = _lang(await get_user(pool, message.from_user.id))

    if idx < len(langs):
        await state.update_data(idx=idx, descs=descs)
        prompt = get_text("ask_for_product_desc_tpl", lang, I18N).format(lang=langs[idx].upper())
        await message.answer(prompt)
    else:
        await state.update_data(descs=descs)
        await state.set_state(AddProductFSM.price)
        await message.answer(get_text("ask_for_price", lang, I18N))


@router.message(AddProductFSM.price, F.text)
async def fsm_prod_price(message: Message, state: FSMContext, pool: asyncpg.Pool):
    lang = _lang(await get_user(pool, message.from_user.id))
    try:
        price = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer(get_text("price_only_number", lang, I18N))
        return

    data = await state.get_data()
    await add_product(
        pool=pool,
        category_id=data["cat_id"],
        name_jsonb=data["names"],
        description_jsonb=data["descs"],
        photo_file_id=data["photo"],
        price=price,
    )
    await state.clear()
    await message.answer(get_text("product_added_success", lang, I18N))
    # YAXSHILANDI: Mahsulot qo'shilgach, o'sha kategoriya menyusi ko'rsatiladi
    await display_category_content(message, pool, data["cat_id"])


# Eslatma: show_product_list funksiyasi olib tashlandi.


@router.callback_query(F.data.startswith("list_products_in_cat:"))
async def cb_list_products(call: CallbackQuery, pool: asyncpg.Pool):
    # TUZATILDI: To'g'ri funksiya chaqirilmoqda
    cat_id = int(call.data.split(":")[1])
    await display_category_content(call, pool, cat_id)


# ─────────────────── 5-BOB: MAHSULOT BOSHQARUV ──────────────────────────
# handlers/admin_handlers.py


def _kb_product(prod, lang: str) -> InlineKeyboardMarkup:
    """Mahsulotni boshqarish klaviaturasi, shu jumladan Variantlarni boshqarish tugmasi."""
    has_desc = bool(prod["description"] and json.loads(prod["description"] or "{}"))
    desc_btn = get_text("edit_desc_btn", lang, I18N) if has_desc else get_text("add_desc_btn", lang, I18N)
    toggle_key = "make_unavailable_btn" if prod["is_available"] else "make_available_btn"
    toggle_btn = InlineKeyboardButton(
        text=get_text(toggle_key, lang, I18N), callback_data=f"toggle_availability:{prod['id']}"
    )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_text("edit_name_btn", lang, I18N), callback_data=f"edit_prod_name:{prod['id']}"
                )
            ],
            [
                InlineKeyboardButton(
                    text=get_text("edit_price_btn", lang, I18N), callback_data=f"edit_price:{prod['id']}"
                )
            ],
            [
                InlineKeyboardButton(
                    text=get_text("edit_photo_btn", lang, I18N), callback_data=f"edit_photo:{prod['id']}"
                )
            ],
            [InlineKeyboardButton(text=desc_btn, callback_data=f"edit_desc:{prod['id']}")],
            # — New “Manage Variations” button —
            [
                InlineKeyboardButton(
                    text=get_text("manage_variations_btn", lang, I18N), callback_data=f"manage_variations:{prod['id']}"
                )
            ],
            [toggle_btn],
            [
                InlineKeyboardButton(
                    text=get_text("delete_btn", lang, I18N), callback_data=f"confirm_delete_product:{prod['id']}"
                )
            ],
            [
                InlineKeyboardButton(
                    text=get_text("back_button", lang, I18N), callback_data=f"category:{prod['category_id']}"
                )
            ],
        ]
    )


async def show_product_menu(target, pool: asyncpg.Pool, prod_id: int):
    """Mahsulot tafsilotlari ekranini ko'rsatadi (o'zgarishsiz)."""
    prod = await get_product(pool, prod_id)
    if not prod:
        lang_nf = _lang(await get_user(pool, target.from_user.id))
        msg = get_text("product_not_found", lang_nf, I18N)
        if isinstance(target, CallbackQuery):
            await target.answer(msg, show_alert=True)
        else:
            await target.answer(msg)
        return

    lang = _lang(await get_user(pool, target.from_user.id))
    desc_block = ""
    if prod["description"]:
        desc_dct = json.loads(prod["description"])
        if desc_dct:
            desc_block = "\n" + (desc_dct.get(lang) or next(iter(desc_dct.values())))

    caption = (
        f"<b>{_prod_name(prod, lang)}</b>\n"
        f"{get_text('price_label', lang, I18N)}<code>{prod['price']}</code>{desc_block}"
    )

    kb = _kb_product(prod, lang)

    if isinstance(target, CallbackQuery):
        await target.message.delete()
        await target.message.answer_photo(prod["photo_file_id"], caption=caption, reply_markup=kb, parse_mode="HTML")
        await target.answer()
    else:
        await target.answer_photo(prod["photo_file_id"], caption=caption, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("product:"))
async def cb_product_menu(call: CallbackQuery, pool: asyncpg.Pool):
    try:
        # callback_datani uch qismga ajratamiz: prefix, id, page
        _, prod_id_str, _ = call.data.split(":")
        prod_id = int(prod_id_str)
    except (ValueError, IndexError):
        return await call.answer("Invalid product data", show_alert=True)

    await show_product_menu(call, pool, prod_id)


@router.callback_query(F.data.startswith("confirm_delete_product:"))
async def cb_confirm_delete_product(call: CallbackQuery, pool: asyncpg.Pool):
    prod_id = int(call.data.split(":", 1)[1])
    prod = await get_product(pool, prod_id)
    if not prod:
        lang = _lang(await get_user(pool, call.from_user.id))
        await call.answer(get_text("product_not_found", lang, I18N), show_alert=True)
        return

    lang = _lang(await get_user(pool, call.from_user.id))
    text = get_text("confirm_delete_tpl", lang, I18N).format(name=_prod_name(prod, lang))
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅", callback_data=f"final_delete_product:{prod_id}")],
            [InlineKeyboardButton(text=get_text("back_button", lang, I18N), callback_data=f"product:{prod_id}")],
        ]
    )
    await call.message.edit_caption(caption=text, reply_markup=kb)
    await call.answer()


@router.callback_query(F.data.startswith("final_delete_product:"))
async def cb_final_delete_product(call: CallbackQuery, pool: asyncpg.Pool):
    prod_id = int(call.data.split(":", 1)[1])
    prod = await get_product(pool, prod_id)
    if not prod:
        lang = _lang(await get_user(pool, call.from_user.id))
        await call.answer(get_text("product_not_found", lang, I18N), show_alert=True)
        return

    await archive_product(pool, prod_id)
    lang = _lang(await get_user(pool, call.from_user.id))
    await call.answer(get_text("product_deleted_success", lang, I18N), show_alert=True)

    # TUZATILDI: Mahsulot o'chirilgandan so'ng, to'g'ri menyuga qaytariladi
    await display_category_content(call, pool, prod["category_id"])


# ───────────── 6-BOB: NARXNI TAHRIRLASH FSM ─────────────────────────────
class EditProductPriceFSM(StatesGroup):
    waiting_price = State()


@router.callback_query(F.data.startswith("edit_price:"))
async def cb_edit_price(call: CallbackQuery, state: FSMContext, pool: asyncpg.Pool):
    prod_id = int(call.data.split(":")[1])
    lang = _lang(await get_user(pool, call.from_user.id))
    await state.set_state(EditProductPriceFSM.waiting_price)
    await state.update_data(prod_id=prod_id)
    await call.message.answer(get_text("ask_for_new_price", lang, I18N))
    await call.answer()


@router.message(EditProductPriceFSM.waiting_price, F.text)
async def fsm_new_price(message: Message, state: FSMContext, pool: asyncpg.Pool):
    lang = _lang(await get_user(pool, message.from_user.id))
    try:
        new_price = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer(get_text("price_only_number", lang, I18N))
        return

    prod_id = (await state.get_data())["prod_id"]
    await update_product_price(pool, prod_id, new_price)
    await state.clear()
    await message.answer(get_text("price_updated", lang, I18N))
    await show_product_menu(message, pool, prod_id)


# ───────────── 7-BOB: NOMNI TAHRIRLASH FSM ──────────────────────────────
class EditProductNameFSM(StatesGroup):
    waiting_name = State()


@router.callback_query(F.data.startswith("edit_prod_name:"))
async def cb_edit_prod_name(call: CallbackQuery, state: FSMContext, pool: asyncpg.Pool):
    prod_id = int(call.data.split(":")[1])
    user = await get_user(pool, call.from_user.id)
    lang = _lang(user)

    enabled_langs_records = await get_enabled_languages(pool)
    if not enabled_langs_records:
        await call.message.answer(get_text("no_enabled_languages_error", lang, LEXICON))
        await call.answer()
        return

    langs = [rec["code"] for rec in enabled_langs_records]

    await state.set_state(EditProductNameFSM.waiting_name)
    await state.update_data(prod_id=prod_id, langs=langs, idx=0, names={})
    prompt = get_text("ask_for_new_prod_name_tpl", lang, I18N).format(lang=langs[0].upper())
    await call.message.answer(prompt)
    await call.answer()


@router.message(EditProductNameFSM.waiting_name, F.text)
async def fsm_new_prod_name(message: Message, state: FSMContext, pool: asyncpg.Pool):
    data = await state.get_data()
    prod_id = data["prod_id"]
    langs, idx, names = data["langs"], data["idx"], data["names"]
    names[langs[idx]] = message.text.strip()
    idx += 1
    lang = _lang(await get_user(pool, message.from_user.id))

    if idx < len(langs):
        await state.update_data(idx=idx, names=names)
        prompt = get_text("ask_for_new_prod_name_tpl", lang, I18N).format(lang=langs[idx].upper())
        await message.answer(prompt)
    else:
        await update_product_name(pool, prod_id, names)
        await state.clear()
        await message.answer(get_text("name_updated", lang, I18N))
        await show_product_menu(message, pool, prod_id)


# ───────────── 8-BOB: RASMNI TAHRIRLASH FSM ──────────────────────
class EditProductPhotoFSM(StatesGroup):
    waiting_photo = State()


@router.callback_query(F.data.startswith("edit_photo:"))
async def cb_edit_photo(call: CallbackQuery, state: FSMContext, pool: asyncpg.Pool):
    prod_id = int(call.data.split(":")[1])
    lang = _lang(await get_user(pool, call.from_user.id))
    await state.set_state(EditProductPhotoFSM.waiting_photo)
    await state.update_data(prod_id=prod_id)
    await call.message.answer(get_text("ask_for_new_photo", lang, I18N))
    await call.answer()


@router.message(EditProductPhotoFSM.waiting_photo, F.photo)
async def fsm_new_photo(message: Message, state: FSMContext, pool: asyncpg.Pool):
    prod_id = (await state.get_data())["prod_id"]
    await update_product_photo(pool, prod_id, message.photo[-1].file_id)
    await state.clear()
    lang = _lang(await get_user(pool, message.from_user.id))
    await message.answer(get_text("photo_updated", lang, I18N))
    await show_product_menu(message, pool, prod_id)


@router.message(EditProductPhotoFSM.waiting_photo)
async def fsm_photo_expected_edit(message: Message, pool: asyncpg.Pool):
    lang = _lang(await get_user(pool, message.from_user.id))
    await message.answer(get_text("no_photo_warning", lang, I18N))


# ──────────── 9-BOB: TAVSIF QO‘SHISH/TAHRIRLASH FSM ───────────────────
class EditProductDescFSM(StatesGroup):
    waiting_desc = State()


@router.callback_query(F.data.startswith("edit_desc:"))
async def cb_edit_desc(call: CallbackQuery, state: FSMContext, pool: asyncpg.Pool):
    prod_id = int(call.data.split(":")[1])
    user = await get_user(pool, call.from_user.id)
    lang = _lang(user)

    enabled_langs_records = await get_enabled_languages(pool)
    if not enabled_langs_records:
        await call.message.answer(get_text("no_enabled_languages_error", lang, LEXICON))
        await call.answer()
        return

    langs = [rec["code"] for rec in enabled_langs_records]

    await state.set_state(EditProductDescFSM.waiting_desc)
    await state.update_data(prod_id=prod_id, langs=langs, idx=0, descs={})
    prompt = get_text("ask_for_product_desc_tpl", lang, I18N).format(lang=langs[0].upper())
    await call.message.answer(prompt)
    await call.answer()


@router.message(EditProductDescFSM.waiting_desc, F.text == "⏭️")
async def fsm_skip_desc_lang(message: Message, state: FSMContext, pool: asyncpg.Pool):
    data = await state.get_data()
    idx, langs = data["idx"] + 1, data["langs"]
    await state.update_data(idx=idx)
    lang = _lang(await get_user(pool, message.from_user.id))

    if idx < len(langs):
        prompt = get_text("ask_for_product_desc_tpl", lang, I18N).format(lang=langs[idx].upper())
        await message.answer(prompt)
    else:
        await _finalize_desc(message, state, pool)


@router.message(EditProductDescFSM.waiting_desc, F.text)
async def fsm_collect_desc(message: Message, state: FSMContext, pool: asyncpg.Pool):
    data = await state.get_data()
    langs, idx, descs = data["langs"], data["idx"], data["descs"]
    descs[langs[idx]] = message.text.strip()
    await state.update_data(descs=descs)
    await fsm_skip_desc_lang(message, state, pool)


async def _finalize_desc(message: Message, state: FSMContext, pool: asyncpg.Pool):
    data = await state.get_data()
    prod_id, descs = data["prod_id"], data["descs"]
    await update_product_description(pool, prod_id, descs)
    await state.clear()
    lang = _lang(await get_user(pool, message.from_user.id))
    await message.answer(get_text("description_updated", lang, I18N))
    await show_product_menu(message, pool, prod_id)


@router.callback_query(F.data.startswith("toggle_availability:"))
async def cb_toggle_product_availability(call: CallbackQuery, pool: asyncpg.Pool):
    """
    Callback: "toggle_availability:<product_id>"
    — tanlangan mahsulotning mavjudlik flagini teskari qiladi,
    so‘ng yangilangan menyuni ko‘rsatadi.
    """
    try:
        _, prod_id_str = call.data.split(":", 1)
        prod_id = int(prod_id_str)
    except (ValueError, IndexError):
        # Callback ma’lumotlari noto‘g‘ri bo‘lsa ogohlantirish
        return await call.answer("Xato mahsulot identifikatori", show_alert=True)

    # Mahsulotning is_available flagini yangilash
    await toggle_product_availability(pool, prod_id)

    # Yangilangan holatni admin interfeysida qayta chizish
    await show_product_menu(call, pool, prod_id)
