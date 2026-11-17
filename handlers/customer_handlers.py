# handlers/customer_handlers.py (Navigatsiya to'liq tuzatilgan versiya)
import html
import json
import logging
import re
from collections import Counter
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from typing import Any

import asyncpg
from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from core.config import Settings
from core.filters import is_order_owner
from core.notify import notify_staff
from db_helpers import (
    count_products_in_category,
    count_subcategories,
    count_toplevel_categories,
    create_order,
    get_cafe_settings,
    get_category,
    get_order,
    get_order_items_with_names,
    get_paginated_sql_params,
    get_product,
    get_product_variations,
    get_products_in_category,
    get_subcategories,
    get_toplevel_categories,
    get_user,
    get_user_orders,
    get_variation_details_with_product_name,
    set_user_selected_language,
    transition_order_status,
)
from locales.lexicon import LEXICON
from utils.geo_utils import is_within_delivery_zone
from utils.keyboards import build_customer_settings_menu, build_pagination_keyboard
from utils.lexicon_utils import SUPPORTED_LANGUAGES, get_i18n_name, get_text
from utils.working_hours import is_accepting_orders

logger = logging.getLogger(__name__)
router = Router(name="customer")

DEFAULT_CANCEL_WINDOW_MINUTES = 5


class ProductQuantityFSM(StatesGroup):
    choosing_quantity = State()


# ---------- Yordamchi funksiyalar ----------
def _lang(user: dict) -> str:
    return user.get("selected_language_code") or user.get("language_code") or "uz"


def get_product_display_name(prod_record, lang_code: str) -> str:
    names = json.loads(prod_record["name"])
    return names.get(lang_code) or next(iter(names.values()))


async def _cancel_window_minutes(pool: asyncpg.Pool) -> int:
    """Bekor qilish oynasi (daqiqa): bazadan, bo'lmasa standart qiymat."""
    cafe = await get_cafe_settings(pool)
    value = cafe.get("cancel_window_minutes") if cafe else None
    try:
        return int(value) if value is not None else DEFAULT_CANCEL_WINDOW_MINUTES
    except (TypeError, ValueError):
        return DEFAULT_CANCEL_WINDOW_MINUTES


# ---------- Markaziy menyu funksiyasi (YANGILANGAN) ----------
async def show_customer_category_content(
    obj: CallbackQuery | Message,
    pool: asyncpg.Pool,
    category_id: int | None,
    current_page: int = 0,
    parent_page: int = 0,  # Bu avvalgi menyuning sahifasini saqlaydi
) -> tuple[str, InlineKeyboardMarkup]:
    """
    Mijoz uchun menyu matnini va klaviaturasini tayyorlab, QAYTARADI.
    Navigatsiya mantiqi to'liq tuzatilgan.
    """
    user = await get_user(pool, obj.from_user.id)
    if not user:
        return "Error: User not found", InlineKeyboardMarkup(inline_keyboard=[])

    lang = _lang(user)
    max_per_page = 10
    kb: InlineKeyboardMarkup
    caption: str
    items = []

    # Orqaga qaytish mantiqi
    back_callback_data = "go_to_main_menu"  # Standart qiymat

    if category_id is None:  # Bosh menyu (eng yuqori darajadagi kategoriyalar)
        total = await count_toplevel_categories(pool)
        offset, limit = get_paginated_sql_params(current_page, page_size=max_per_page)
        records = await get_toplevel_categories(pool, offset, limit)
        items = [(c["id"], f"📂 {get_i18n_name(c['name'], lang)}") for c in records]

        kb = build_pagination_keyboard(
            items_list=items,
            current_page=current_page,
            total_items=total,
            callback_prefix="customer_view_cat",
            lang=lang,
            back_callback_data=back_callback_data,
            page_callback=lambda p: f"customer_page:{p}",
            max_items_per_page=max_per_page,
        )
        caption = get_text("category_list_title", lang, LEXICON)
    else:  # Ichki kategoriyalar yoki mahsulotlar
        parent_cat = await get_category(pool, category_id)
        parent_id_for_back = parent_cat["parent_id"] if parent_cat else None

        # <<< ASOSIY TUZATISH: ORQAGA QAYTISH MANTIG'I
        if parent_id_for_back:
            # Agar ota kategoriya mavjud bo'lsa, o'sha ota kategoriyaga qaytamiz.
            # `parent_page` - bu ota kategoriyalar ro'yxatining sahifasi.
            back_callback_data = f"customer_view_cat:{parent_id_for_back}:{parent_page}"
        else:
            # Agar ota kategoriya yo'q bo'lsa (ya'ni, bu eng yuqori darajadagi kategoriya),
            # unda bosh menyuning tegishli sahifasiga qaytamiz.
            back_callback_data = f"customer_page:{parent_page}"

        sub_count = await count_subcategories(pool, category_id)
        if sub_count > 0:  # Ichki kategoriyalarni ko'rsatish
            total = sub_count
            offset, limit = get_paginated_sql_params(current_page, page_size=max_per_page)
            records = await get_subcategories(pool, category_id, offset, limit)
            items = [(c["id"], f"📂 {get_i18n_name(c['name'], lang)}") for c in records]

            kb = build_pagination_keyboard(
                items_list=items,
                current_page=current_page,
                total_items=total,
                callback_prefix="customer_view_cat",
                lang=lang,
                back_callback_data=back_callback_data,
                page_callback=lambda p: f"customer_cat_page:{category_id}:{p}:{parent_page}",
                max_items_per_page=max_per_page,
            )
            caption = get_text("subcategory_title_tpl", lang, LEXICON).format(
                name=get_i18n_name(parent_cat["name"], lang)
            )
        else:  # Mahsulotlarni ko'rsatish
            total = await count_products_in_category(pool, category_id)
            offset, limit = get_paginated_sql_params(current_page, page_size=max_per_page)
            records = await get_products_in_category(pool, category_id, offset, limit)
            items = [(p["id"], f"🍽️ {get_i18n_name(p['name'], lang)}") for p in records]

            kb = build_pagination_keyboard(
                items_list=items,
                current_page=current_page,
                total_items=total,
                callback_prefix="customer_view_prod",
                lang=lang,
                back_callback_data=back_callback_data,
                page_callback=lambda p: f"customer_cat_page:{category_id}:{p}:{parent_page}",
                max_items_per_page=max_per_page,
            )
            caption = get_text("product_list_title", lang, LEXICON)

    # Qo'shimcha tugmalarni qo'shish
    if category_id is None:
        additional_buttons = [
            InlineKeyboardButton(text=get_text("cart_button", lang, LEXICON), callback_data="view_cart"),
            InlineKeyboardButton(
                text=get_text("settings_button", lang, LEXICON), callback_data="customer_settings_menu"
            ),
        ]
        kb.inline_keyboard.insert(-1, additional_buttons)

    text_to_send = caption if items else get_text("category_empty_msg", lang, LEXICON)

    return text_to_send, kb


# ---------- Handlerlar (TUZATILGAN QISMLAR) ----------


@router.callback_query(F.data.startswith("customer_page:"))
async def cb_customer_page(call: CallbackQuery, pool: asyncpg.Pool):
    _, page_str = call.data.split(":")
    page = int(page_str)

    # Bosh menyu uchun parent_page 0 ga teng
    text, kb = await show_customer_category_content(call, pool, None, current_page=page, parent_page=0)
    try:
        await call.message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        pass
    await call.answer()


@router.callback_query(F.data.startswith("customer_cat_page:"))
async def cb_customer_category_page(call: CallbackQuery, pool: asyncpg.Pool):
    """Kategoriya ichidagi (ichki kategoriyalar yoki mahsulotlar) ro'yxatning boshqa sahifasi."""
    try:
        _, cat_str, page_str, parent_str = call.data.split(":")
        cat_id, page, parent_page = int(cat_str), int(page_str), int(parent_str)
    except ValueError:
        return await call.answer()
    text, kb = await show_customer_category_content(
        call, pool, category_id=cat_id, current_page=max(page, 0), parent_page=parent_page
    )
    try:
        await call.message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        pass
    await call.answer()


@router.callback_query(F.data.startswith("customer_view_cat:"))
async def cb_customer_view_category(call: CallbackQuery, pool: asyncpg.Pool):
    _, cat_str, parent_str = call.data.split(":")
    cat_id, parent_page = int(cat_str), int(parent_str)

    # <<< TUZATISH: oldingi menyu sahifasini (`parent_page`) to'g'ri uzatyapmiz
    # va yangi menyuning joriy sahifasi (`current_page`) 0 dan boshlanadi
    text, kb = await show_customer_category_content(
        call, pool, category_id=cat_id, current_page=0, parent_page=parent_page
    )
    try:
        await call.message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        pass
    await call.answer()


@router.callback_query(F.data.startswith("customer_view_prod:"))
async def cb_customer_view_product(call: CallbackQuery, state: FSMContext, pool: asyncpg.Pool):
    """
    Mahsulot sahifasini ko‘rsatadi:
    - oddiy mahsulot uchun miqdor tanlash FSM’ini ishga tushiradi
    - variatsiyali mahsulot uchun har bir variatsiya uchun alohida tugma yaratadi
    """
    # 1) Callback ma'lumotini ajratamiz: prod_id va joriy sahifa
    _, prod_str, page_str = call.data.split(":")
    prod_id = int(prod_str)
    page_of_prod_list = int(page_str)

    # 2) Mahsulot va foydalanuvchi ma'lumotlarini yuklaymiz
    prod = await get_product(pool, prod_id)
    user = await get_user(pool, call.from_user.id)
    lang = _lang(user)
    if not prod:
        await call.answer(get_text("product_not_found", lang, LEXICON), show_alert=True)
        return

    # 3) Mahsulot tavsifi (agar mavjud bo‘lsa)
    desc = ""
    if prod.get("description"):
        try:
            d = json.loads(prod["description"])
            desc = "\n" + (d.get(lang) or next(iter(d.values())))
        except Exception:
            pass

    # 4) Asosiy caption tayyorlash
    caption = (
        f"<b>{get_product_display_name(prod, lang)}</b>\n"
        f"<i>{desc.strip()}</i>\n\n"
        f"Narx: <code>{prod['price']} so'm dan boshlanadi</code>"
    )

    # 5) Agar mahsulot variatsiyalarga ega bo‘lsa
    if prod.get("has_variations"):
        button_rows: list[list[InlineKeyboardButton]] = []
        variations = await get_product_variations(pool, prod_id)
        for var in variations:
            var_name = get_i18n_name(var["name"], lang)
            btn_text = f"{var_name} — {var['price']} so'm"
            button_rows.append(
                [
                    InlineKeyboardButton(
                        text=btn_text,
                        # <<< O'ZGARTIRILDI: add_variation_to_cart o‘rniga:
                        # "customer_view_variation:{variation_id}:{page}"
                        callback_data=f"customer_view_variation:{var['id']}:{page_of_prod_list}",
                    )
                ]
            )
        # Orqaga tugma
        button_rows.append(
            [
                InlineKeyboardButton(
                    text=get_text("back_button", lang, LEXICON),
                    callback_data=f"customer_back_to_cat:{prod['category_id']}:{page_of_prod_list}",
                )
            ]
        )
        kb = InlineKeyboardMarkup(inline_keyboard=button_rows)
        # Captionni variatsiya tanlash uchun moslaymiz
        caption = (
            f"<b>{get_product_display_name(prod, lang)}</b>\n<i>{desc.strip()}</i>\n\nVariantlardan birini tanlang:"
        )

    # 6) Aks holda oddiy mahsulot: miqdor FSM’ini ishga tushiramiz
    else:
        await state.set_state(ProductQuantityFSM.choosing_quantity)
        await state.update_data(
            item_type="product", item_id=prod_id, quantity=1, category_id=prod["category_id"], page=page_of_prod_list
        )
        from utils.keyboards import build_quantity_keyboard

        kb = build_quantity_keyboard(
            item_type="product",
            item_id=prod_id,
            quantity=1,
            lang=lang,
            category_id=prod["category_id"],
            page=page_of_prod_list,
        )

    # 7) Eskirgan xabarni o‘chirib, yangi rasm + klaviatura yuboramiz
    await call.message.delete()
    await call.message.answer_photo(prod["photo_file_id"], caption=caption, reply_markup=kb, parse_mode="HTML")
    await call.answer()


# handlers/customer_handlers.py


@router.callback_query(F.data.startswith("customer_view_variation:"))
async def cb_view_variation_detail(call: CallbackQuery, state: FSMContext, pool: asyncpg.Pool):
    """
    Variant tafsilot sahifasi:
    - Callback ma'lumotidan variant_id va sahifa raqamini o‘qiymiz
    - get_variation_details_with_product_name’dan barcha zarur maydonlarni olamiz
    - FSMni tanlov holatiga o‘rnatib, kerakli data saqlaymiz
    - build_quantity_keyboard yordamida miqdor klaviaturasini yasaymiz
    - Eskirgan xabarni o‘chirib, yangi rasm + klaviatura yuboramiz
    """
    # 1) parametrlari ajratib olinadi
    _, var_str, page_str = call.data.split(":")
    variation_id = int(var_str)
    page_of_prod_list = int(page_str)

    # 2) variant va ota mahsulot ma'lumotlari
    rec = await get_variation_details_with_product_name(pool, variation_id)
    if not rec:
        await call.answer("Variant topilmadi", show_alert=True)
        return

    user = await get_user(pool, call.from_user.id)
    lang = _lang(user)

    # 3) rasmni aniqlash: agar variatsiya rasmi bo‘lsa, undan,
    # aks holda ota mahsulotning rasmidan foydalanamiz
    photo_id = rec["photo_file_id"]
    if not photo_id:
        prod = await get_product(pool, rec["product_id"])
        photo_id = prod["photo_file_id"]

    # 4) FSMni miqdor tanlash holatiga o‘rnatamiz
    await state.set_state(ProductQuantityFSM.choosing_quantity)
    await state.update_data(
        item_type="variation", item_id=variation_id, quantity=1, category_id=rec["category_id"], page=page_of_prod_list
    )

    # 5) miqdor klaviaturasini yaratamiz
    from utils.keyboards import build_quantity_keyboard

    kb = build_quantity_keyboard(
        item_type="variation",
        item_id=variation_id,
        quantity=1,
        lang=lang,
        category_id=rec["category_id"],
        page=page_of_prod_list,
    )

    # 6) eskirgan xabarni o‘chirib, yangi variant rasmi bilan miqdor klaviaturasini yuboramiz
    #    caption uchun faqat variant nomi va narxni ko‘rsatamiz
    var_names = json.loads(rec["variation_name"])
    var_display = var_names.get(lang) or next(iter(var_names.values()))
    caption = f"<b>{var_display}</b>\n\nNarx: <code>{rec['price']} so'm</code>"

    await call.message.delete()
    await call.message.answer_photo(photo_id, caption=caption, reply_markup=kb, parse_mode="HTML")
    await call.answer()


# 3) Miqdorni oshirish
@router.callback_query(F.data.startswith("incr_qty:"))
async def cb_incr_qty(call: CallbackQuery, state: FSMContext, pool: asyncpg.Pool):
    data = await state.get_data()
    # miqdorni oshiramiz
    quantity = data.get("quantity", 1) + 1
    await state.update_data(quantity=quantity)
    # klaviaturani qayta qurish
    from utils.keyboards import build_quantity_keyboard

    kb = build_quantity_keyboard(
        item_type=data["item_type"],
        item_id=data["item_id"],
        quantity=quantity,
        lang=_lang(await get_user(pool, call.from_user.id)),
        category_id=data["category_id"],
        page=data["page"],
    )
    await call.message.edit_reply_markup(reply_markup=kb)
    await call.answer()


# 4) Miqdorni kamaytirish
@router.callback_query(F.data.startswith("decr_qty:"))
async def cb_decr_qty(call: CallbackQuery, state: FSMContext, pool: asyncpg.Pool):
    data = await state.get_data()
    # miqdor hech qachon 1 dan past bo‘lmasin
    quantity = max(1, data.get("quantity", 1) - 1)
    await state.update_data(quantity=quantity)
    # klaviaturani yangilaymiz
    from utils.keyboards import build_quantity_keyboard

    kb = build_quantity_keyboard(
        item_type=data["item_type"],
        item_id=data["item_id"],
        quantity=quantity,
        lang=_lang(await get_user(pool, call.from_user.id)),
        category_id=data["category_id"],
        page=data["page"],
    )
    await call.message.edit_reply_markup(reply_markup=kb)
    await call.answer()


# 5) Savatga qo'shish tugmasi bosilganda
@router.callback_query(F.data.startswith("add_N_to_cart:"))
async def cb_add_N_to_cart(call: CallbackQuery, state: FSMContext, pool: asyncpg.Pool):
    # FSMdagi barcha ma'lumotlarni olamiz
    data = await state.get_data()

    # Asosiy savat ro'yxatini olamiz yoki bo'sh ro'yxat yaratamiz
    cart = data.get("cart_items", [])

    # Kerakli miqdordagi mahsulotni savatga qo'shamiz
    for _ in range(data["quantity"]):
        cart.append({"type": data["item_type"], "id": data["item_id"]})

    # <<< ASOSIY TUZATISH: FSMni to'liq tozalamaymiz! >>>
    # 1. Faqat holat nomini (state) tozalaymiz
    await state.set_state(state=None)
    # 2. Faqat kerakli `cart_items`ni xotiraga qayta yozamiz.
    #    Bu avtomatik ravishda vaqtinchalik (quantity, item_id) ma'lumotlarni o'chiradi.
    await state.update_data(cart_items=cart)

    # Foydalanuvchiga muvaffaqiyat haqida bildirishnoma
    user = await get_user(pool, call.from_user.id)
    lang = _lang(user)

    # Qaysi mahsulot qo'shilganini aniqlaymiz
    if data["item_type"] == "product":
        item_record = await get_product(pool, data["item_id"])
        name = get_product_display_name(item_record, lang)
    else:  # variation
        item_record = await get_variation_details_with_product_name(pool, data["item_id"])
        var_names = json.loads(item_record["variation_name"])
        name = var_names.get(lang) or next(iter(var_names.values()))

    await call.answer(
        get_text("product_added_to_cart_tpl", lang, LEXICON).format(name=name),
        show_alert=True,
    )

    # Mahsulotlar ro'yxati oynasiga qaytamiz
    text, kb = await show_customer_category_content(
        call,
        pool,
        category_id=data["category_id"],
        current_page=data["page"],
        parent_page=0,  # Bu yerda parent_page logikasi kerak bo'lishi mumkin, hozircha 0
    )
    await call.message.delete()
    await call.message.answer(text, reply_markup=kb)


# Bu handler endi deyarli ishlatilmaydi, lekin qoldiramiz.
@router.callback_query(F.data.startswith("prod_page:"))
async def cb_prod_page(call: CallbackQuery, pool: asyncpg.Pool):
    _, cat_str, page_str = call.data.split(":")
    category_id, page = int(cat_str), int(page_str)

    text, kb = await show_customer_category_content(call, pool, category_id, current_page=page, parent_page=page)
    try:
        await call.message.delete()
        await call.message.answer(text, reply_markup=kb)
    except TelegramBadRequest:
        try:
            await call.message.edit_text(text, reply_markup=kb)
        except TelegramBadRequest:
            pass

    await call.answer()


# qolgan barcha kodlar (savatcha, buyurtma va hokazo) o'zgarishsiz qoladi...


@router.callback_query(F.data.startswith("add_to_cart:"))
async def cb_add_to_cart(call: CallbackQuery, state: FSMContext, pool: asyncpg.Pool):
    """
    Append a simple product to the FSM cart as {'type':'product','id': product_id}.
    """
    prod_id = int(call.data.split(":", 1)[1])
    data = await state.get_data()
    cart: list[dict] = data.get("cart_items", [])
    cart.append({"type": "product", "id": prod_id})
    await state.update_data(cart_items=cart)

    user = await get_user(pool, call.from_user.id)
    lang = _lang(user)
    prod = await get_product(pool, prod_id)
    name = get_product_display_name(prod, lang) if prod else f"ID {prod_id}"
    await call.answer(get_text("product_added_to_cart_tpl", lang, LEXICON).format(name=name), show_alert=True)


@router.callback_query(F.data.startswith("add_variation_to_cart:"))
async def cb_add_variation_to_cart(call: CallbackQuery, state: FSMContext, pool: asyncpg.Pool):
    """
    Append a variation to the FSM cart as {'type':'variation','id': variation_id}.
    """
    var_id = int(call.data.split(":", 1)[1])
    data = await state.get_data()
    cart: list[dict] = data.get("cart_items", [])
    cart.append({"type": "variation", "id": var_id})
    await state.update_data(cart_items=cart)

    user = await get_user(pool, call.from_user.id)
    lang = _lang(user)
    # Fetch both variation and product names for feedback
    rec = await get_variation_details_with_product_name(pool, var_id)
    var_names = json.loads(rec["variation_name"])
    var_name = var_names.get(lang) or next(iter(var_names.values()))
    await call.answer(f"✅ {var_name} — {rec['price']} so'm qo'shildi!", show_alert=True)


async def show_cart_view(obj: CallbackQuery | Message, state: FSMContext, pool: asyncpg.Pool):
    """
    Renders the cart from the new FSM state list of dicts:
      - counts unique (type,id) pairs
      - fetches price & name for products vs. variations
      - builds increment/decrement/delete callbacks encoding both type and id
    """
    data = await state.get_data()
    cart: list[dict] = data.get("cart_items", [])
    user = await get_user(pool, obj.from_user.id)
    lang = _lang(user)

    # Bo'sh savatcha holati
    if not cart:
        # <<< TUZATISH: `text=` va `callback_data=` kalit so'zlari qo'shildi
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=get_text("back_button", lang, LEXICON), callback_data="go_to_main_menu")]
            ]
        )
        text = get_text("cart_empty", lang, LEXICON)
        if isinstance(obj, CallbackQuery):
            await obj.message.edit_text(text, reply_markup=kb)
            await obj.answer()
        else:
            await obj.answer(text, reply_markup=kb)
        return

    # Elementlarni sanash (qolgan qismi o'zgarishsiz)
    counts = Counter((item["type"], item["id"]) for item in cart)
    lines, rows, total_sum = [], [], Decimal("0.0")

    for (kind, item_id), qty in counts.items():
        if kind == "product":
            prod = await get_product(pool, item_id)
            if not prod:
                continue
            name = get_product_display_name(prod, lang)
            price = Decimal(str(prod["price"]))
        else:  # variation
            rec = await get_variation_details_with_product_name(pool, item_id)
            if not rec:
                continue
            base_names = json.loads(rec["product_name"])
            var_names = json.loads(rec["variation_name"])
            product_display = base_names.get(lang) or next(iter(base_names.values()))
            variation_display = var_names.get(lang) or next(iter(var_names.values()))
            name = f"{product_display} — {variation_display}"
            price = Decimal(str(rec["price"]))

        subtotal = price * qty
        total_sum += subtotal
        lines.append(
            get_text("cart_item_template", lang, LEXICON).format(name=name, quantity=qty, total_sum=f"{subtotal:.2f}")
        )

        rows.append([InlineKeyboardButton(text=f"🍽️ {name} × {qty}", callback_data="noop")])
        rows.append(
            [
                InlineKeyboardButton(text="➖", callback_data=f"decr_item:{kind}:{item_id}"),
                InlineKeyboardButton(text="➕", callback_data=f"incr_item:{kind}:{item_id}"),
                InlineKeyboardButton(text="❌", callback_data=f"del_item:{kind}:{item_id}"),
            ]
        )

    rows += [
        [InlineKeyboardButton(text=get_text("place_order_button", lang, LEXICON), callback_data="place_order")],
        [InlineKeyboardButton(text=get_text("clear_cart_button", lang, LEXICON), callback_data="clear_cart")],
        [InlineKeyboardButton(text=get_text("back_button", lang, LEXICON), callback_data="go_to_main_menu")],
    ]

    text = (
        f"{get_text('view_cart_title', lang, LEXICON)}\n\n"
        f"{chr(10).join(lines)}\n\n"
        f"{get_text('total_price', lang, LEXICON).format(total=f'{total_sum:.2f}')}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=rows)

    if isinstance(obj, CallbackQuery):
        try:
            await obj.message.edit_text(text, reply_markup=kb)
        except TelegramBadRequest:
            await obj.message.delete()
            await obj.message.answer(text, reply_markup=kb)
        await obj.answer()
    else:
        await obj.answer(text, reply_markup=kb)


@router.callback_query(F.data == "view_cart")
async def cb_view_cart(call: CallbackQuery, state: FSMContext, pool: asyncpg.Pool) -> Any:
    await show_cart_view(call, state, pool)


@router.callback_query(F.data == "clear_cart")
async def cb_clear_cart(call: CallbackQuery, state: FSMContext, pool: asyncpg.Pool):
    user = await get_user(pool, call.from_user.id)
    lang = _lang(user)

    await state.update_data(cart_items=[])
    await call.answer(get_text("cart_cleared_alert", lang, LEXICON), show_alert=True)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=get_text("back_button", lang, LEXICON), callback_data="go_to_main_menu")]
        ]
    )
    await call.message.edit_text(get_text("cart_empty", lang, LEXICON), reply_markup=kb)


@router.callback_query(F.data.startswith("incr_item:"))
async def cb_increment_item(call: CallbackQuery, state: FSMContext, pool: asyncpg.Pool):
    """
    Increments one unit of the given (type,id) in cart by appending another entry.
    """
    _, kind, item_id = call.data.split(":")
    data = await state.get_data()
    cart = data.get("cart_items", [])
    cart.append({"type": kind, "id": int(item_id)})
    await state.update_data(cart_items=cart)
    await show_cart_view(call, state, pool)


@router.callback_query(F.data.startswith("decr_item:"))
async def cb_decrement_item(call: CallbackQuery, state: FSMContext, pool: asyncpg.Pool):
    """
    Removes one unit of the given (type,id) from cart by popping the first match.
    """
    _, kind, item_id = call.data.split(":")
    data = await state.get_data()
    cart = data.get("cart_items", [])
    for i, entry in enumerate(cart):
        if entry["type"] == kind and entry["id"] == int(item_id):
            cart.pop(i)
            break
    await state.update_data(cart_items=cart)
    await show_cart_view(call, state, pool)


@router.callback_query(F.data.startswith("del_item:"))
async def cb_delete_item(call: CallbackQuery, state: FSMContext, pool: asyncpg.Pool):
    """
    Deletes all units of the given (type,id) from cart.
    """
    _, kind, item_id = call.data.split(":")
    data = await state.get_data()
    cart = data.get("cart_items", [])
    cart = [e for e in cart if not (e["type"] == kind and e["id"] == int(item_id))]
    await state.update_data(cart_items=cart)
    await show_cart_view(call, state, pool)


class OrderFSM(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_location = State()


@router.callback_query(F.data == "place_order")
async def cb_place_order(call: CallbackQuery, state: FSMContext, pool: asyncpg.Pool, settings: Settings):
    # 1. Kafe ish vaqtini tekshirish (TIMEZONE bo'yicha, yarim tundan o'tuvchi smenalar ham)
    user = await get_user(pool, call.from_user.id)
    lang = _lang(user)
    cafe = await get_cafe_settings(pool)
    start_time: time | None = cafe.get("work_hours_start")
    end_time: time | None = cafe.get("work_hours_end")
    buffer_minutes: int = cafe.get("order_acceptance_buffer_minutes") or 0

    if start_time and end_time:
        if not is_accepting_orders(datetime.now(settings.tz), start_time, end_time, buffer_minutes, settings.tz):
            await call.answer(
                get_text("cafe_is_closed_tpl", lang, LEXICON).format(
                    start_time=start_time.strftime("%H:%M"), end_time=end_time.strftime("%H:%M")
                ),
                show_alert=True,
            )
            return

    # 2. Savatni tekshirish
    data = await state.get_data()
    cart_items: list[dict] = data.get("cart_items", [])

    if not cart_items:
        return await call.answer(get_text("cart_is_empty_error", lang, LEXICON), show_alert=True)

    # 3. Yakuniy buyurtma ro'yxatini tuzish va summani hisoblash
    counts = Counter((i["type"], i["id"]) for i in cart_items)
    final_order_details, total_amount = [], Decimal("0.0")

    for (kind, item_id), qty in counts.items():
        if kind == "product":
            prod = await get_product(pool, item_id)
            if not prod:
                continue
            price, product_id, variation_id = Decimal(str(prod["price"])), item_id, None
        else:  # variation
            rec = await get_variation_details_with_product_name(pool, item_id)
            if not rec:
                continue
            price, product_id, variation_id = Decimal(str(rec["price"])), rec["product_id"], item_id

        final_order_details.append(
            {
                "product_id": product_id,
                "variation_id": variation_id,
                "quantity": qty,
                # <<< ASOSIY TUZATISH: `Decimal` obyektini matnga o'giramiz
                "price_per_item": str(price),
            }
        )
        total_amount += price * qty

    # 4. FSM xotirasiga saqlash va keyingi bosqichga o'tish
    await state.update_data(final_order_details=final_order_details, total_amount=str(total_amount))
    await state.set_state(OrderFSM.waiting_for_name)

    await call.message.answer(get_text("ask_for_customer_name", lang, LEXICON), reply_markup=ReplyKeyboardRemove())
    await call.answer()


@router.message(OrderFSM.waiting_for_name, F.text)
async def fsm_get_customer_name(message: Message, state: FSMContext, pool: asyncpg.Pool) -> Any:
    customer_name = message.text.strip()
    lang = _lang(await get_user(pool, message.from_user.id))
    if not customer_name or len(customer_name) > 255:  # orders.customer_name is VARCHAR(255)
        await message.answer(get_text("ask_for_customer_name", lang, LEXICON))
        return

    await state.update_data(customer_name=customer_name)
    await state.set_state(OrderFSM.waiting_for_phone)

    phone_btn = KeyboardButton(text=get_text("send_phone_button", lang, LEXICON), request_contact=True)
    kb = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[[phone_btn]], one_time_keyboard=True)
    await message.answer(get_text("ask_for_phone", lang, LEXICON), reply_markup=kb)


@router.message(OrderFSM.waiting_for_phone, F.contact)
async def fsm_get_phone(message: Message, state: FSMContext, pool: asyncpg.Pool):
    phone = message.contact.phone_number
    await state.update_data(customer_phone=phone)
    await state.set_state(OrderFSM.waiting_for_location)
    lang = _lang(await get_user(pool, message.from_user.id))
    await message.answer(get_text("ask_for_location", lang, LEXICON), reply_markup=ReplyKeyboardRemove())


@router.message(OrderFSM.waiting_for_phone, F.text)
async def fsm_get_phone_text(message: Message, state: FSMContext, pool: asyncpg.Pool):
    lang = _lang(await get_user(pool, message.from_user.id))
    phone_text = message.text.strip()

    if re.fullmatch(r"\+?\d{9,15}$", phone_text):
        await state.update_data(customer_phone=phone_text)
        await state.set_state(OrderFSM.waiting_for_location)
        await message.answer(get_text("ask_for_location", lang, LEXICON), reply_markup=ReplyKeyboardRemove())
    else:
        await message.answer(get_text("invalid_phone_format", lang, LEXICON))


# handlers/customer_handlers.py


@router.message(OrderFSM.waiting_for_location, F.location)
async def fsm_get_location(message: Message, state: FSMContext, pool: asyncpg.Pool, settings: Settings):
    """Buyurtmani yakunlaydi va yangi daily_id bilan xabar yuboradi."""
    lang = _lang(await get_user(pool, message.from_user.id))
    lat, lon = message.location.latitude, message.location.longitude

    # Yetkazib berish zonasi checkout paytida ham tekshiriladi (faqat /start da emas).
    if not is_within_delivery_zone(await get_cafe_settings(pool), lat, lon):
        logger.info("Checkout location outside delivery zone", extra={"user_id": message.from_user.id})
        await message.answer(get_text("order_location_out_of_zone", lang, LEXICON))
        return  # holat o'zgarmaydi: mijoz boshqa lokatsiya yuborishi mumkin

    data = await state.get_data()
    customer_name: str = data["customer_name"]
    customer_phone: str = data["customer_phone"]
    final_order_details: list = data["final_order_details"]
    total_amount: Decimal = Decimal(data["total_amount"])

    order_id, daily_id = await create_order(
        pool=pool,
        user_id=message.from_user.id,
        final_order_details=final_order_details,
        total_amount=total_amount,
        phone=customer_phone,
        latitude=lat,
        longitude=lon,
        customer_name=customer_name,
    )
    logger.info("Order created", extra={"order_id": order_id, "daily_id": daily_id, "user_id": message.from_user.id})

    await state.clear()
    await message.answer(get_text("order_placed_success", lang, LEXICON))

    def build(usr_lang: str):
        text = get_text("new_order_for_admin_tpl", usr_lang, LEXICON).format(
            id=order_id,
            daily_id=daily_id,
            customer_name=html.escape(customer_name),
            phone=html.escape(customer_phone),
            total=total_amount,
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=get_text("view_order_details_btn", usr_lang, LEXICON),
                        callback_data=f"view_order_details:{order_id}",
                    )
                ]
            ]
        )
        return text, kb

    await notify_staff(message.bot, pool, settings, build, parse_mode="HTML")


@router.message(OrderFSM.waiting_for_location)
async def fsm_location_expected(message: Message, state: FSMContext, pool: asyncpg.Pool) -> Any:
    lang = _lang(await get_user(pool, message.from_user.id))
    await message.answer(get_text("ask_for_location_again", lang, LEXICON))


@router.callback_query(F.data == "my_orders")
async def cb_my_orders(call: CallbackQuery, pool: asyncpg.Pool) -> Any:
    await show_my_orders_list(call, pool)


@router.callback_query(F.data.startswith("customer_view_order_details:"))
async def cb_customer_view_order_details(call: CallbackQuery, pool: asyncpg.Pool):
    """Mijozning bitta buyurtma tafsilotlarini to'liq ko'rsatadi."""
    # 1) Order ID olish va tekshirish
    order_id = int(call.data.split(":")[1])
    order = await get_order(pool, order_id)
    if not order or order["user_id"] != call.from_user.id:
        lang = _lang(await get_user(pool, call.from_user.id))
        await call.answer(get_text("order_not_found_alert", lang, LEXICON), show_alert=True)
        return

    # 2) Foydalanuvchi tili
    lang = _lang(await get_user(pool, call.from_user.id))

    # 3) YANGI: Bekor qilish oynasi DB’dan olinadi (ENV o‘chirildi)
    cancel_minutes = await _cancel_window_minutes(pool)

    # 4) Bekor qilish mumkinligini aniqlash
    can_cancel = order["status"] == "pending" and datetime.now(UTC) - order["created_at"] <= timedelta(
        minutes=cancel_minutes
    )

    # 5) Buyurtma ichidagi elementlarni tayyorlash
    items = await get_order_items_with_names(pool, order_id)
    item_lines = [
        f"- {json.loads(it['name']).get(lang) or next(iter(json.loads(it['name']).values()))} × {it['quantity']}"
        for it in items
    ]
    items_block = "\n".join(item_lines)

    # 6) Xabar matni
    text = get_text("order_details_tpl", lang, LEXICON).format(
        id=order["id"],
        daily_id=order["daily_id"],
        customer_label=get_text("customer_label", lang, LEXICON),
        name=order["customer_name"],
        phone_label=get_text("phone_label", lang, LEXICON),
        phone=order["customer_phone"],
        items_label=get_text("items_label", lang, LEXICON),
        items=items_block,
        status_label=get_text("status_label", lang, LEXICON),
        status=get_text(f"status_{order['status']}", lang, LEXICON),
        total=order["total_amount"],
    )

    # 7) Inline-klaviatura: agar bekor qilish mumkin bo‘lsa, tegishli tugma qo‘shiladi
    buttons = []
    if can_cancel:
        buttons.append(
            InlineKeyboardButton(
                text=get_text("cancel_order_button", lang, LEXICON), callback_data=f"confirm_cancel_order:{order_id}"
            )
        )
    # Har doim “Orqaga” tugmasi mavjud
    buttons.append(InlineKeyboardButton(text=get_text("back_button", lang, LEXICON), callback_data="my_orders"))
    kb = InlineKeyboardMarkup(inline_keyboard=[[b] for b in buttons])

    # 8) Xabarni tahrirlash va javob berish
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()


@router.callback_query(F.data.startswith("confirm_cancel_order:"))
async def cb_confirm_customer_cancel(call: CallbackQuery, pool: asyncpg.Pool) -> Any:
    """Buyurtmani bekor qilishni tasdiqlash oynasini ko'rsatadi."""
    order_id = int(call.data.split(":")[1])

    # <<< Buyurtmani bazadan olamiz, daily_id ni bilish uchun
    order = await get_order(pool, order_id)
    user = await get_user(pool, call.from_user.id)
    lang = _lang(user)
    if not is_order_owner(order, call.from_user.id):
        return await call.answer(get_text("order_not_found_alert", lang, LEXICON), show_alert=True)

    # <<< format() ga endi order['daily_id'] to'g'ri beriladi
    text = get_text("confirm_cancel_prompt", lang, LEXICON).format(daily_id=order["daily_id"])

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅", callback_data=f"final_cancel_order:{order_id}")],
            [InlineKeyboardButton(text="❌", callback_data=f"customer_view_order_details:{order_id}")],
        ]
    )

    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()


@router.callback_query(F.data.startswith("final_cancel_order:"))
async def cb_final_customer_cancel(call: CallbackQuery, pool: asyncpg.Pool, settings: Settings) -> Any:
    """Buyurtmani bekor qilishni yakunlaydi va adminga xabar yuboradi."""
    order_id = int(call.data.split(":")[1])
    lang = _lang(await get_user(pool, call.from_user.id))

    # Bekor qilish oynasi serverda ham tekshiriladi (eski tugma bilan kechikib bekor qilib bo'lmaydi).
    window = await _cancel_window_minutes(pool)
    order = await transition_order_status(
        pool,
        order_id,
        from_statuses=("pending",),
        to_status="canceled",
        user_id=call.from_user.id,
        created_after=datetime.now(UTC) - timedelta(minutes=window),
    )
    if order is None:
        await call.answer(get_text("unable_to_cancel_alert", lang, LEXICON), show_alert=True)
        return

    logger.info("Order canceled by customer", extra={"order_id": order_id, "user_id": call.from_user.id})
    await call.answer(get_text("order_canceled_alert", lang, LEXICON), show_alert=True)

    def build(usr_lang: str):
        text = get_text("order_canceled_for_admin_tpl", usr_lang, LEXICON).format(
            id=order_id, daily_id=order["daily_id"]
        )
        return text, None

    await notify_staff(call.bot, pool, settings, build)
    await show_my_orders_list(call, pool)


# handlers/customer_handlers.py


async def show_my_orders_list(target: Message | CallbackQuery, pool: asyncpg.Pool):
    """Mijozning barcha buyurtmalari ro'yxatini to'liq ko'rsatadi."""
    user_id = target.from_user.id
    user = await get_user(pool, user_id)
    lang = _lang(user)
    orders = await get_user_orders(pool, user_id)

    if orders:
        rows = []
        for o in orders:
            btn_text = get_text("my_order_list_item_tpl", lang, LEXICON).format(
                daily_id=o["daily_id"],
                total=o["total_amount"],  # <<< TUZATISH: "so'm" bu yerdan olib tashlandi
                status=get_text(f"status_{o['status']}", lang, LEXICON),
            )
            rows.append([InlineKeyboardButton(text=btn_text, callback_data=f"customer_view_order_details:{o['id']}")])
        text = get_text("my_orders_list_title", lang, LEXICON)
    else:
        rows = []
        text = get_text("no_orders_yet_history", lang, LEXICON)

    rows.append(
        [InlineKeyboardButton(text=get_text("back_button", lang, LEXICON), callback_data="customer_settings_menu")]
    )
    kb = InlineKeyboardMarkup(inline_keyboard=rows)

    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=kb)
        await target.answer()
    else:
        await target.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("customer_back_to_cat:"))
async def cb_customer_back_to_category(call: CallbackQuery, pool: asyncpg.Pool):
    """
    Mahsulot oynasidan orqaga bosilganda ishlaydi va menyuni
    to'g'ri sahifadan ochib beradi. (YANGI FUNKSIYA)
    """
    _, cat_str, page_str = call.data.split(":")
    cat_id, page = int(cat_str), int(page_str)

    # Ota kategoriyani topamiz, uning ota sahifasini bilish uchun
    parent_cat = await get_category(pool, cat_id)
    parent_page = 0  # Agar topilmasa, standart 0
    if parent_cat and parent_cat["parent_id"]:
        # Bu qism kelajakda ichma-ich menyudan qaytishda kerak bo'ladi,
        # hozircha 0 bo'lib tursa ham bo'laveradi.
        pass

    text, kb = await show_customer_category_content(
        call, pool, category_id=cat_id, current_page=page, parent_page=parent_page
    )

    # Rasm bilan bo'lgan xabarni matnga almashtirish uchun avval o'chiramiz
    await call.message.delete()
    await call.message.answer(text, reply_markup=kb)
    await call.answer()


async def _customer_delivery_answer(
    call: CallbackQuery,
    pool: asyncpg.Pool,
    settings: Settings,
    *,
    to_status: str,
    customer_text_key: str,
    courier_text_key: str,
    staff_text_key: str,
) -> None:
    """Mijozning "yetkazildi / yetkazilmadi" javobi.

    Faqat buyurtma EGASI va faqat 'delivering' holatida ishlaydi: atomik
    transition_order_status(user_id=...) orqali tekshiriladi.
    """
    lang = _lang(await get_user(pool, call.from_user.id))
    try:
        order_id = int(call.data.split(":", 1)[1])
    except (IndexError, ValueError):
        await call.answer(get_text("order_not_found_alert", lang, LEXICON), show_alert=True)
        return

    order = await transition_order_status(
        pool, order_id, from_statuses=("delivering",), to_status=to_status, user_id=call.from_user.id
    )
    if order is None:
        logger.warning(
            "Rejected delivery confirmation",
            extra={"user_id": call.from_user.id, "callback_data": call.data},
        )
        await call.answer(get_text("order_not_found_alert", lang, LEXICON), show_alert=True)
        return

    logger.info("Delivery answered by customer", extra={"order_id": order_id, "status": to_status})
    try:
        await call.message.edit_text(get_text(customer_text_key, lang, LEXICON), reply_markup=None)
    except TelegramBadRequest:
        pass

    # Kuryerga yuborilgan avvalgi xabarni tahrirlash
    courier_id = order.get("courier_id")
    courier_msg_id = order.get("courier_message_id")
    if courier_id and courier_msg_id:
        courier_lang = _lang(await get_user(pool, courier_id))
        try:
            await call.bot.edit_message_text(
                get_text(courier_text_key, courier_lang, LEXICON),
                chat_id=courier_id,
                message_id=courier_msg_id,
                reply_markup=None,
            )
        except Exception:
            logger.info("Could not edit courier message", extra={"order_id": order_id}, exc_info=True)

    def build(usr_lang: str):
        return get_text(staff_text_key, usr_lang, LEXICON).format(daily_id=order["daily_id"]), None

    await notify_staff(call.bot, pool, settings, build)
    await call.answer()


@router.callback_query(F.data.startswith("cust_confirm_ok:"))
async def cb_cust_confirm_ok(call: CallbackQuery, pool: asyncpg.Pool, settings: Settings):
    await _customer_delivery_answer(
        call,
        pool,
        settings,
        to_status="completed",
        customer_text_key="customer_delivery_thanks",
        courier_text_key="delivery_success_for_courier",
        staff_text_key="order_completed_notification_tpl",
    )


@router.callback_query(F.data.startswith("cust_confirm_no:"))
async def cb_cust_confirm_no(call: CallbackQuery, pool: asyncpg.Pool, settings: Settings):
    await _customer_delivery_answer(
        call,
        pool,
        settings,
        to_status="disputed",
        customer_text_key="customer_dispute_info",
        courier_text_key="delivery_failed_for_courier",
        staff_text_key="alert_order_rejected_tpl",
    )


@router.callback_query(F.data == "customer_settings_menu")
async def cb_customer_settings_menu(call: CallbackQuery, state: FSMContext, pool: asyncpg.Pool):
    """Mijozning shaxsiy sozlamalar menyusini ko'rsatadi."""
    user = await get_user(pool, call.from_user.id)
    lang = user.get("selected_language_code") or user.get("language_code") or "uz"
    kb = build_customer_settings_menu(lang)
    await call.message.edit_text(get_text("settings_title", lang, LEXICON), reply_markup=kb)
    await call.answer()


# ------------------ LANGUAGE SWITCHER (o'zgarishsiz) --------------------
@router.callback_query(F.data == "change_language")
async def cb_change_language(call: CallbackQuery, pool: asyncpg.Pool):
    user = await get_user(pool, call.from_user.id)
    lang = user.get("selected_language_code") or user.get("language_code") or "uz"

    lang_buttons = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_select:uz")],
            [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_select:ru")],
            [InlineKeyboardButton(text="🇺🇸 English", callback_data="lang_select:en")],
            [InlineKeyboardButton(text=get_text("back_button", lang, LEXICON), callback_data="customer_settings_menu")],
        ]
    )
    await call.message.edit_text(get_text("change_language_button", lang, LEXICON), reply_markup=lang_buttons)
    await call.answer()


@router.callback_query(F.data.startswith("lang_select:"))
async def cb_language_selected(call: CallbackQuery, state: FSMContext, pool: asyncpg.Pool):
    lang_code = call.data.split(":", 1)[1]
    if lang_code not in SUPPORTED_LANGUAGES:
        return await call.answer()
    await set_user_selected_language(pool, call.from_user.id, lang_code)
    await call.answer(get_text("language_set_alert", lang_code, LEXICON), show_alert=True)
    await cb_customer_settings_menu(call, state, pool)
