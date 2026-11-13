# handlers/admin/categories.py
"""Kategoriyalarni boshqarish (qo'shish, ko'rish, tahrirlash, arxivlash)."""

from __future__ import annotations

import logging
from math import ceil

import asyncpg
from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from db_helpers import (
    add_category,
    archive_category,
    count_products_in_category,
    count_subcategories,
    count_toplevel_categories,
    get_category,
    get_enabled_languages,
    get_paginated_sql_params,
    get_products_in_category,
    get_subcategories,
    get_toplevel_categories,
    get_user,
    update_category_name,
)
from handlers.admin.common import I18N, _cat_name, _lang, _prod_name
from locales.lexicon import LEXICON
from utils.keyboards import build_pagination_keyboard
from utils.lexicon_utils import get_text

logger = logging.getLogger(__name__)
router = Router(name="admin.categories")


# ──────────────────────── 1-BOB: KATEGORIYA QO‘SHISH ─────────────────────
class AddCategoryFSM(StatesGroup):
    waiting_name = State()


@router.callback_query(F.data.startswith("add_category"))
async def cb_add_category(call: CallbackQuery, state: FSMContext, pool: asyncpg.Pool):
    user = await get_user(pool, call.from_user.id)

    # Tillar ro'yxati endi bazadan olinadi
    enabled_langs_records = await get_enabled_languages(pool)
    lang = _lang(user)
    if not enabled_langs_records:
        await call.message.answer(get_text("no_enabled_languages_error", lang, LEXICON))
        await call.answer()
        return

    langs = [rec["code"] for rec in enabled_langs_records]

    await state.set_state(AddCategoryFSM.waiting_name)
    await state.update_data(
        parent_id=None,
        langs=langs,
        idx=0,
        names={},
    )
    prompt = get_text("ask_for_cat_name_tpl", lang, I18N).format(lang=langs[0].upper())
    await call.message.edit_text(prompt)
    await call.answer()


@router.callback_query(F.data.startswith("add_subcategory_to:"))
async def cb_add_subcategory(call: CallbackQuery, state: FSMContext, pool: asyncpg.Pool):
    parent_id = int(call.data.split(":")[1])
    user = await get_user(pool, call.from_user.id)
    lang = _lang(user)

    enabled_langs_records = await get_enabled_languages(pool)
    if not enabled_langs_records:
        # TUZATILDI: Xato xabari endi LEXICON'dan olinmoqda.
        await call.message.answer(get_text("no_enabled_languages_error", lang, LEXICON))
        await call.answer()
        return

    langs = [rec["code"] for rec in enabled_langs_records]

    await state.set_state(AddCategoryFSM.waiting_name)
    await state.update_data(parent_id=parent_id, langs=langs, idx=0, names={})
    prompt = get_text("ask_for_subcat_name_tpl", lang, I18N).format(lang=langs[0].upper())
    await call.message.edit_text(prompt)
    await call.answer()


@router.message(AddCategoryFSM.waiting_name, F.text)
async def fsm_cat_name(message: Message, state: FSMContext, pool: asyncpg.Pool):
    data = await state.get_data()
    langs, idx, names = data["langs"], data["idx"], data["names"]
    names[langs[idx]] = message.text.strip()
    idx += 1
    lang = _lang(await get_user(pool, message.from_user.id))

    if idx < len(langs):
        await state.update_data(idx=idx, names=names)
        prompt = get_text("ask_for_cat_name_tpl", lang, I18N).format(lang=langs[idx].upper())
        await message.answer(prompt)
    else:
        await add_category(pool, names, data.get("parent_id"))
        await state.clear()
        await message.answer(get_text("category_added_success", lang, I18N))
        # TUZATILDI: Keraksiz funksiya o'rniga to'g'ri funksiya chaqirilmoqda.
        await display_category_management_menu(message, pool)


# ─────────────────── KATEGORIYA BOSHQARUV ───────────────────
class EditCategoryNameFSM(StatesGroup):
    waiting_name = State()


def _kb_category(cat, lang: str) -> InlineKeyboardMarkup:
    """Kategoriyani boshqarish klaviaturasi."""
    # Orqaga qaytish mantiqi to'g'ri, o'zgarishsiz qoladi.
    back_cb = f"category:{cat['parent_id']}" if cat["parent_id"] else "manage_categories"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_text("add_subcategory_btn", lang, I18N),
                    callback_data=f"add_subcategory_to:{cat['id']}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=get_text("add_product_btn", lang, I18N),
                    callback_data=f"add_product:{cat['id']}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=get_text("list_products_btn", lang, I18N),
                    callback_data=f"list_products_in_cat:{cat['id']}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=get_text("edit_name_btn", lang, I18N),
                    callback_data=f"edit_category_name:{cat['id']}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=get_text("delete_btn", lang, I18N),
                    callback_data=f"confirm_delete_category:{cat['id']}",
                )
            ],
            [InlineKeyboardButton(text=get_text("back_button", lang, I18N), callback_data=back_cb)],
        ]
    )


# ─────────────────────── KATEGORIYANI KO‘RISH ───────────────────────
@router.callback_query(F.data.startswith(("category:", "subcategory:")))
async def cb_view_category_details(call: CallbackQuery, pool: asyncpg.Pool):
    try:
        parts = call.data.split(":")
        cat_id = int(parts[1])
        # Agar callback_data'da uchinchi qism (sahifa raqami) bo'lsa, uni olamiz.
        # Agar bo'lmasa, standart 0 qiymatini beramiz.
        parent_page = int(parts[2]) if len(parts) > 2 else 0
    except (ValueError, IndexError):
        return await call.answer("Invalid category data", show_alert=True)

    await display_category_content(call, pool, cat_id=cat_id, page=0, parent_page=parent_page)


@router.callback_query(F.data.startswith("subcategory_page:"))
async def cb_subcategory_pagination(call: CallbackQuery, pool: asyncpg.Pool):
    # Bu funksiya to'g'ri ishlaydi, `display_category_content` ga tayanadi.
    try:
        _, cat_id_str, page_str = call.data.split(":", 2)
        cat_id, page = int(cat_id_str), int(page_str)
    except (ValueError, IndexError):
        return await call.answer("Invalid page", show_alert=True)
    await display_category_content(call, pool, cat_id, page)


@router.callback_query(F.data.startswith("product_page:"))
async def cb_product_pagination(call: CallbackQuery, pool: asyncpg.Pool):
    # Bu funksiya to'g'ri ishlaydi, `display_category_content` ga tayanadi.
    try:
        _, cat_id_str, page_str = call.data.split(":", 2)
        cat_id, page = int(cat_id_str), int(page_str)
    except (ValueError, IndexError):
        return await call.answer("Invalid page", show_alert=True)
    await display_category_content(call, pool, cat_id, page)


@router.callback_query(F.data.startswith("edit_category_name:"))
async def cb_edit_cat_name(call: CallbackQuery, state: FSMContext, pool: asyncpg.Pool):
    cat_id = int(call.data.split(":")[1])
    cat = await get_category(pool, cat_id)
    if not cat:
        await call.answer(get_text("product_not_found", "uz", I18N), show_alert=True)
        return

    user = await get_user(pool, call.from_user.id)
    lang = _lang(user)

    enabled_langs_records = await get_enabled_languages(pool)
    if not enabled_langs_records:
        # TUZATILDI: Xato xabari endi LEXICON'dan olinmoqda.
        await call.message.answer(get_text("no_enabled_languages_error", lang, LEXICON))
        await call.answer()
        return

    langs = [rec["code"] for rec in enabled_langs_records]

    await state.set_state(EditCategoryNameFSM.waiting_name)
    await state.update_data(cat_id=cat_id, langs=langs, idx=0, names={})
    prompt = get_text("ask_for_new_cat_name_tpl", lang, I18N).format(lang=langs[0].upper())
    await call.message.answer(prompt)
    await call.answer()


@router.message(EditCategoryNameFSM.waiting_name, F.text)
async def fsm_new_cat_name(message: Message, state: FSMContext, pool: asyncpg.Pool):
    data = await state.get_data()
    cat_id = data["cat_id"]
    langs, idx, names = data["langs"], data["idx"], data["names"]
    names[langs[idx]] = message.text.strip()
    idx += 1

    lang = _lang(await get_user(pool, message.from_user.id))
    if idx < len(langs):
        await state.update_data(idx=idx, names=names)
        prompt = get_text("ask_for_new_cat_name_tpl", lang, I18N).format(lang=langs[idx].upper())
        await message.answer(prompt)
        return

    await update_category_name(pool, cat_id, names)
    await state.clear()

    await message.answer(get_text("category_name_updated", lang, I18N))
    # TUZATILDI: Keraksiz funksiya o'rniga to'g'ri funksiya chaqirilmoqda.
    await display_category_management_menu(message, pool)


@router.callback_query(F.data.startswith("confirm_delete_category:"))
async def cb_confirm_delete_category(call: CallbackQuery, pool: asyncpg.Pool):
    cat_id = int(call.data.split(":", 1)[1])
    cat = await get_category(pool, cat_id)
    user = await get_user(pool, call.from_user.id)
    lang = _lang(user)

    text = get_text("confirm_delete_tpl", lang, I18N).format(name=_cat_name(cat, lang))
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅", callback_data=f"final_delete_category:{cat_id}")],
            [InlineKeyboardButton(text=get_text("back_button", lang, I18N), callback_data=f"category:{cat_id}")],
        ]
    )
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()


@router.callback_query(F.data.startswith("final_delete_category:"))
async def cb_final_delete_category(call: CallbackQuery, pool: asyncpg.Pool):
    cat_id = int(call.data.split(":", 1)[1])
    cat = await get_category(pool, cat_id)
    if not cat:
        lang = _lang(await get_user(pool, call.from_user.id))
        await call.answer(get_text("category_not_found", lang, I18N), show_alert=True)
        return

    await archive_category(pool, cat_id)

    lang = _lang(await get_user(pool, call.from_user.id))
    await call.answer(get_text("category_deleted_success", lang, I18N), show_alert=True)
    # TUZATILDI: To'g'ri menyu funksiyasi chaqirilmoqda
    await display_category_management_menu(call, pool)


# ─────────────────────  MARKAZIY YORDAMCHI FUNKSIYALAR  ─────────────────────
async def display_category_management_menu(
    target: CallbackQuery | Message,
    pool: asyncpg.Pool,
    page: int = 0,
):
    """
    Admin uchun asosiy kategoriya boshqaruv menyusi (tozalangan).
    """
    user = await get_user(pool, target.from_user.id)
    lang = _lang(user)

    offset, limit = get_paginated_sql_params(page, 10)
    cats = await get_toplevel_categories(pool, offset, limit)
    total_cats = await count_toplevel_categories(pool)

    # TUZATILDI: Orqaga qaytish mantiqi soddalashtirildi.
    back_cb = "admin_main_menu"

    item_pairs = [(c["id"], _cat_name(c, lang)) for c in cats]

    # TUZATILDI: keraksiz `user_object` parametri olib tashlandi.
    kb = build_pagination_keyboard(
        items_list=item_pairs,
        current_page=page,
        total_items=total_cats,
        callback_prefix="category",
        lang=lang,
        back_callback_data=back_cb,
        page_callback=lambda p: f"category_page:{p}",
    )

    kb.inline_keyboard.insert(
        0, [InlineKeyboardButton(text=get_text("add_category_btn", lang, LEXICON), callback_data="add_category")]
    )

    total_pages = max(1, ceil(total_cats / 10))
    title = f"{get_text('category_list_title', lang, LEXICON)} ({page + 1}/{total_pages})"

    if isinstance(target, CallbackQuery):
        await target.answer()
        try:
            await target.message.edit_text(title, reply_markup=kb)
        except TelegramBadRequest:
            await target.message.answer(title, reply_markup=kb)
    else:
        await target.answer(title, reply_markup=kb)


@router.callback_query(F.data == "manage_categories")
async def cb_manage_categories(call: CallbackQuery, pool: asyncpg.Pool):
    await display_category_management_menu(call, pool, page=0)


@router.callback_query(F.data.startswith("category_page:"))
async def cb_category_pagination(call: CallbackQuery, pool: asyncpg.Pool):
    try:
        page = int(call.data.split(":", 1)[1])
    except (IndexError, ValueError):
        return await call.answer("Invalid page", show_alert=True)
    await display_category_management_menu(call, pool, page=page)


async def display_category_content(
    target: CallbackQuery | Message,
    pool: asyncpg.Pool,
    cat_id: int,
    page: int = 0,
    parent_page: int = 0,  # <-- SHU QISM QO'SHILSIN
):
    """Kategoriya ichidagi ma'lumotlarni ko'rsatadi (tozalangan)."""
    user = await get_user(pool, target.from_user.id)
    lang = _lang(user)

    sub_total = await count_subcategories(pool, cat_id)
    prod_total = await count_products_in_category(pool, cat_id)
    total_items = sub_total or prod_total

    offset, limit = get_paginated_sql_params(page, 10)
    if sub_total > 0:
        records = await get_subcategories(pool, cat_id, offset, limit)
        items = [(r["id"], f"📂 {_cat_name(r, lang)}") for r in records]
        callback_prefix = "subcategory"
        title_key = "subcategory_list_title"
    else:
        records = await get_products_in_category(pool, cat_id, offset, limit)
        items = [(r["id"], f"🍽️ {_prod_name(r, lang)}") for r in records]
        callback_prefix = "product"
        title_key = "product_list_title"

    parent = await get_category(pool, cat_id)
    # TUZATILDI: Orqaga qaytish mantiqi to'g'rilandi
    back_cb = f"category:{parent['parent_id']}" if parent and parent["parent_id"] else "manage_categories"

    # TUZATILDI: keraksiz `user_object` parametri olib tashlandi.
    kb = build_pagination_keyboard(
        items_list=items,
        current_page=page,
        total_items=total_items,
        callback_prefix=callback_prefix,
        lang=lang,
        back_callback_data=back_cb,
        page_callback=(
            (lambda p: f"subcategory_page:{cat_id}:{p}") if sub_total > 0 else (lambda p: f"product_page:{cat_id}:{p}")
        ),
    )

    # ... (qolgan qismi deyarli o'zgarishsiz, faqat keraksiz tugmalar o'chiriladi)
    kb.inline_keyboard.insert(
        -1,
        [
            InlineKeyboardButton(
                text=get_text("add_subcategory_btn" if sub_total > 0 else "add_product_btn", lang, LEXICON),
                callback_data=f"add_subcategory_to:{cat_id}" if sub_total > 0 else f"add_product:{cat_id}",
            ),
            InlineKeyboardButton(
                text=get_text("manage_category_details_btn", lang, LEXICON),
                callback_data=f"manage_category_details:{cat_id}",
            ),
        ],
    )

    total_pages = max(1, ceil(total_items / 10))
    caption = f"{get_text(title_key, lang, LEXICON)} ({page + 1}/{total_pages})"

    # ... (xabar yuborish qismi o'zgarishsiz)
    if isinstance(target, CallbackQuery):
        await target.answer()
        try:
            await target.message.edit_text(caption, reply_markup=kb)
        except TelegramBadRequest:
            await target.message.delete()
            await target.message.answer(caption, reply_markup=kb)
    else:
        await target.answer(caption, reply_markup=kb)


@router.callback_query(F.data.startswith("manage_category_details:"))
async def cb_manage_category_details(call: CallbackQuery, pool: asyncpg.Pool):
    cat_id = int(call.data.split(":", 1)[1])
    cat = await get_category(pool, cat_id)
    if not cat:
        lang = _lang(await get_user(pool, call.from_user.id))
        return await call.answer(get_text("category_not_found", lang, LEXICON), show_alert=True)

    lang = _lang(await get_user(pool, call.from_user.id))
    kb = _kb_category(cat, lang)
    await call.message.edit_text(_cat_name(cat, lang), reply_markup=kb)
    await call.answer()
