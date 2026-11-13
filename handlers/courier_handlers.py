# handlers/courier_handlers.py
"""Kuryer paneli.

Router darajasida ``IsCourier`` filtri bor (faqat faol kuryerlar). Bundan tashqari
har bir buyurtma bo'yicha amal faqat shu buyurtmaga TAYINLANGAN kuryer uchun va
faqat 'delivering' holatida ishlaydi — aks holda mijoz ismi/telefoni oshkor bo'lmaydi.
"""

from __future__ import annotations

import html
import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from asyncpg import Pool

from core.filters import IsCourier, is_assigned_courier
from core.notify import user_lang
from db_helpers import get_courier_active_orders, get_order, get_user
from handlers.admin.common import parse_int_arg
from locales.lexicon import LEXICON
from utils.keyboards import build_courier_panel_menu, build_pagination_keyboard
from utils.lexicon_utils import get_text

logger = logging.getLogger(__name__)
router = Router(name="courier")
router.message.filter(IsCourier())
router.callback_query.filter(IsCourier())


async def _get_own_active_order(call: CallbackQuery, pool: Pool, lang: str):
    """Buyurtmani faqat chaqiruvchi kuryerga tayinlangan va yetkazilayotgan bo'lsa qaytaradi."""
    order_id = parse_int_arg(call.data)
    order = await get_order(pool, order_id) if order_id is not None else None
    if not is_assigned_courier(order, call.from_user.id) or order["status"] != "delivering":
        logger.warning(
            "Courier tried to access a delivery that is not theirs",
            extra={"courier_id": call.from_user.id, "callback_data": call.data},
        )
        await call.answer(get_text("order_not_found_alert", lang, LEXICON), show_alert=True)
        return None
    return order


@router.callback_query(F.data.startswith("deliver_confirm:"))
async def cb_deliver_confirm(call: CallbackQuery, pool: Pool):
    """
    Kuriyer “Yetkazdim” tugmasini bosganda — mijozga tasdiqlash so‘rovi yuboriladi
    va kuryerga jo‘natilgan tugmali xabar o‘zgartiriladi.
    """
    courier_lang = user_lang(await get_user(pool, call.from_user.id))
    order = await _get_own_active_order(call, pool, courier_lang)
    if order is None:
        return

    order_id = order["id"]
    customer_lang = user_lang(await get_user(pool, order["user_id"]))

    text = get_text("ask_customer_delivery_confirmation_tpl", customer_lang, LEXICON).format(daily_id=order["daily_id"])
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_text("customer_confirm_delivery_button", customer_lang, LEXICON),
                    callback_data=f"cust_confirm_ok:{order_id}",
                ),
                InlineKeyboardButton(
                    text=get_text("customer_reject_delivery_button", customer_lang, LEXICON),
                    callback_data=f"cust_confirm_no:{order_id}",
                ),
            ]
        ]
    )
    try:
        await call.bot.send_message(order["user_id"], text, reply_markup=kb)
    except Exception:
        logger.warning("Failed to ask customer for confirmation", extra={"order_id": order_id}, exc_info=True)

    try:
        await call.message.edit_text(
            get_text("courier_delivery_requested_alert", courier_lang, LEXICON), reply_markup=None
        )
    except TelegramBadRequest:
        pass
    await call.answer()


DELIVERIES_PER_PAGE = 10


@router.callback_query(F.data.startswith("my_active_deliveries_page:"))
async def cb_my_active_deliveries_page(call: CallbackQuery, pool: Pool):
    page = parse_int_arg(call.data)
    if page is None:
        return await call.answer()
    await cb_my_active_deliveries(call, pool, page=page)


@router.callback_query(F.data == "my_active_deliveries")
async def cb_my_active_deliveries(call: CallbackQuery, pool: Pool, page: int = 0):
    """Kuryerga tayinlangan 'delivering' statusdagi buyurtmalar ro'yxati (sahifalangan)."""
    courier_id = call.from_user.id
    orders = await get_courier_active_orders(pool, courier_id)
    courier_lang = user_lang(await get_user(pool, courier_id))

    if not orders:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=get_text("back_button", courier_lang, LEXICON), callback_data="courier_panel_main"
                    )
                ]
            ]
        )
        await call.message.edit_text(get_text("no_active_deliveries", courier_lang, LEXICON), reply_markup=kb)
        return await call.answer()

    last_page = (len(orders) - 1) // DELIVERIES_PER_PAGE
    page = min(max(page, 0), last_page)
    chunk = orders[page * DELIVERIES_PER_PAGE : (page + 1) * DELIVERIES_PER_PAGE]
    items_list = [
        (
            order["id"],
            get_text("active_delivery_item_tpl", courier_lang, LEXICON).format(
                daily_id=order["daily_id"],
                customer_name=order["customer_name"],
            ),
        )
        for order in chunk
    ]
    kb = build_pagination_keyboard(
        items_list=items_list,
        current_page=page,
        total_items=len(orders),
        callback_prefix="view_delivery_task",
        lang=courier_lang,
        back_callback_data="courier_panel_main",
        page_callback=lambda p: f"my_active_deliveries_page:{p}",
        max_items_per_page=DELIVERIES_PER_PAGE,
    )
    await call.message.edit_text(
        text=get_text("active_deliveries_list_title", courier_lang, LEXICON),
        reply_markup=kb,
    )
    await call.answer()


@router.callback_query(F.data == "courier_panel_main")
async def cb_courier_panel_main(call: CallbackQuery, pool: Pool):
    """Kuryerning asosiy panelini ko'rsatadi."""
    lang = user_lang(await get_user(pool, call.from_user.id))
    await call.message.edit_text(
        get_text("courier_panel_title", lang, LEXICON), reply_markup=build_courier_panel_menu(lang)
    )
    await call.answer()


@router.callback_query(F.data.startswith("view_delivery_task:"))
async def cb_view_delivery_task(call: CallbackQuery, pool: Pool):
    """Kuryer ro'yxatdan buyurtmani tanlaganda uning batafsil vazifasini ko'rsatadi."""
    lang = user_lang(await get_user(pool, call.from_user.id))
    order = await _get_own_active_order(call, pool, lang)
    if order is None:
        return

    text = get_text("new_delivery_for_courier_tpl", lang, LEXICON).format(
        daily_id=order["daily_id"],
        customer_name=html.escape(order["customer_name"] or ""),
        customer_phone=html.escape(order["customer_phone"] or ""),
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_text("view_location_button", lang, LEXICON),
                    url=f"https://www.google.com/maps?q={order['latitude']},{order['longitude']}",
                ),
                InlineKeyboardButton(
                    text=get_text("courier_confirm_delivery_button", lang, LEXICON),
                    callback_data=f"deliver_confirm:{order['id']}",
                ),
            ],
            [InlineKeyboardButton(text=get_text("back_button", lang, LEXICON), callback_data="my_active_deliveries")],
        ]
    )
    try:
        await call.message.edit_text(text=text, reply_markup=kb)
    except TelegramBadRequest:
        pass
    await call.answer()
