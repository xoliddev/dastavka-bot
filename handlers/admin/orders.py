# handlers/admin/orders.py
"""Buyurtmalar paneli: ro'yxatlar, sana filtri, holatlar, kuryer tayinlash, kunlik hisobot."""

from __future__ import annotations

import html
import json
import logging
from datetime import UTC, date, datetime, time, timedelta, tzinfo
from math import ceil

import asyncpg
from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback

from core.config import Settings
from db_helpers import (
    assign_courier_to_order,
    count_orders_by_status,
    count_orders_by_status_and_range,
    get_courier,
    get_couriers_with_status,
    get_daily_report,
    get_order,
    get_order_items_with_names,
    get_orders_by_status_and_range,
    get_orders_by_status_paginated,
    get_paginated_sql_params,
    get_user,
    save_courier_message_id,
    transition_order_status,
)
from handlers.admin.common import I18N, _lang, parse_int_arg
from locales.lexicon import LEXICON
from utils.keyboards import (
    build_date_gateway_menu,
    build_orders_dashboard_keyboard,
    build_pagination_keyboard,
    build_quick_select_menu,
)
from utils.lexicon_utils import get_text
from utils.working_hours import local_day_bounds

logger = logging.getLogger(__name__)
router = Router(name="admin.orders")

# Eslatma: show_new_orders_list funksiyasi olib tashlandi.


# ───── BUYURTMALAR PANELIGA KIRISH ─────────────────────
@router.callback_query(F.data == "admin_view_orders")
async def cb_admin_view_orders(call: CallbackQuery, pool: asyncpg.Pool):
    user = await get_user(pool, call.from_user.id)

    lang = _lang(user)
    # build_orders_dashboard_keyboard endi faqat admin uchun ishlaydi
    kb = build_orders_dashboard_keyboard(lang)
    await call.message.edit_text(get_text("orders_dashboard_title", lang, LEXICON), reply_markup=kb)
    await call.answer()


# ───── Buyurtma holatini o'zgartirish ───────────────────────
async def _notify_customer(call: CallbackQuery, pool: asyncpg.Pool, order, text_key: str) -> None:
    cust_lang = _lang(await get_user(pool, order["user_id"]))
    try:
        await call.bot.send_message(
            order["user_id"],
            get_text(text_key, cust_lang, LEXICON).format(daily_id=order["daily_id"]),
        )
    except Exception:
        logger.warning("Failed to notify customer", extra={"order_id": order["id"]}, exc_info=True)


async def _change_status(
    call: CallbackQuery,
    pool: asyncpg.Pool,
    *,
    from_statuses: tuple[str, ...],
    to_status: str,
    alert_key: str,
    customer_text_key: str | None = None,
):
    """Umumiy holat o'zgartirish: atomik o'tish + admin alerti + mijozga xabar."""
    order_id = parse_int_arg(call.data)
    lang = _lang(await get_user(pool, call.from_user.id))
    if order_id is None:
        return await call.answer(get_text("order_not_found_alert", lang, LEXICON), show_alert=True)

    order = await transition_order_status(pool, order_id, from_statuses=from_statuses, to_status=to_status)
    if order is None:
        # Buyurtma yo'q yoki holati allaqachon o'zgargan (ikki marta bosish, eski tugma, soxta callback)
        return await call.answer(get_text("order_status_conflict_alert", lang, LEXICON), show_alert=True)

    logger.info(
        "Order status changed",
        extra={"order_id": order_id, "status": to_status, "by_admin": call.from_user.id},
    )
    await call.answer(get_text(alert_key, lang, LEXICON), show_alert=True)
    if customer_text_key:
        await _notify_customer(call, pool, order, customer_text_key)
    await show_order_details(call, pool, order_id, answer=False)


@router.callback_query(F.data.startswith("accept_order:"))
async def cb_accept_order(call: CallbackQuery, pool: asyncpg.Pool):
    await _change_status(
        call, pool, from_statuses=("pending",), to_status="processing", alert_key="order_accepted_alert"
    )


@router.callback_query(F.data.startswith("deliver_order:"))
async def cb_deliver_order(call: CallbackQuery, pool: asyncpg.Pool):
    await _change_status(
        call,
        pool,
        from_statuses=("processing",),
        to_status="delivering",
        alert_key="order_delivering_alert",
        customer_text_key="order_status_delivering_tpl",
    )


@router.callback_query(F.data.startswith("complete_order:"))
async def cb_complete_order(call: CallbackQuery, pool: asyncpg.Pool):
    await _change_status(
        call,
        pool,
        from_statuses=("delivering", "disputed"),
        to_status="completed",
        alert_key="order_completed_alert",
        customer_text_key="order_status_completed_tpl",
    )


@router.callback_query(F.data.startswith("view_order_details:"))
async def cb_view_order_details(call: CallbackQuery, pool: asyncpg.Pool):
    """
    Admin buyurtmalar ro'yxatidan birini tanlaganda ishlaydi.
    Vazifasi - callback'ni tahlil qilib, uni asosiy `show_order_details` funksiyasiga uzatish.
    """
    parts = call.data.split(":")
    context = None

    try:
        if len(parts) >= 6:
            # Sana bo'yicha filtrdan kelganda context yaratamiz
            _, order_id_str, st, frm_iso, to_iso, pg_str = parts[:6]
            order_id = int(order_id_str)
            context = dict(status=st, frm=frm_iso, to=to_iso, page=int(pg_str))
        elif len(parts) >= 2:
            # Oddiy ro'yxatdan kelganda
            _, order_id_str = parts[:2]
            order_id = int(order_id_str)
        else:
            raise ValueError("Not enough parts in callback data")

    except (ValueError, IndexError):
        return await call.answer("Xato ma'lumot!", show_alert=True)

    # Barcha mantiqni o'zida saqlagan yagona funksiyani chaqiramiz va context'ni uzatamiz
    await show_order_details(call, pool, order_id, context)


# handlers/admin_handlers.py


async def show_orders_by_status(
    target: CallbackQuery | Message,
    pool: asyncpg.Pool,
    status: str,
    page: int = 0,
):
    """Status bo'yicha buyurtmalar ro'yxatini to'liq ko'rsatadi."""
    user = await get_user(pool, target.from_user.id)
    lang = _lang(user)

    off, lim = get_paginated_sql_params(page, 10)
    orders = await get_orders_by_status_paginated(pool, status, off, lim)
    total = await count_orders_by_status(pool, status)

    items = [
        (
            o["id"],
            get_text("order_list_item_tpl", lang, LEXICON).format(
                daily_id=o["daily_id"],
                total=o["total_amount"],  # <<< TUZATISH: "so'm" bu yerdan olib tashlandi
            ),
        )
        for o in orders
    ]

    back_cb = "admin_view_orders"

    kb = build_pagination_keyboard(
        items_list=items,
        current_page=page,
        total_items=total,
        callback_prefix="view_order_details",
        lang=lang,
        back_callback_data=back_cb,
        page_callback=lambda p: f"orders_by_status_page:{status}:{p}",
    )

    title_key = {
        "pending": "new_orders_list_title",
        "processing": "processing_orders_title",
        "delivering": "delivering_orders_title",
        "completed": "completed_orders_title",
        "disputed": "disputed_orders_title",
        "canceled": "canceled_orders_title",
    }.get(status, "new_orders_list_title")

    total_pages = max(1, ceil(total / 10))
    caption = f"{get_text(title_key, lang, LEXICON)} ({page + 1}/{total_pages})"
    if not orders:
        caption = get_text("no_disputed_orders" if status == "disputed" else "no_new_orders", lang, LEXICON)

    if isinstance(target, CallbackQuery):
        await target.answer()
        try:
            await target.message.edit_text(caption, reply_markup=kb)
        except TelegramBadRequest:
            await target.message.answer(caption, reply_markup=kb)
    else:
        await target.answer(caption, reply_markup=kb)


# handlers/admin_handlers.py


async def show_orders_for_period(
    target: CallbackQuery | Message,
    pool: asyncpg.Pool,
    status: str,
    date_from: date,
    date_to: date,
    page: int = 0,
    tz: tzinfo = UTC,
):
    """Belgilangan sana oralig'idagi buyurtmalar ro'yxatini to'liq ko'rsatadi.

    Sanalar kafe vaqt mintaqasida (TIMEZONE) talqin qilinadi: [date_from 00:00, date_to 00:00).
    """
    user = await get_user(pool, target.from_user.id)
    lang = _lang(user)

    range_start = datetime.combine(date_from, time.min, tzinfo=tz)
    range_end = datetime.combine(date_to, time.min, tzinfo=tz)
    off, lim = get_paginated_sql_params(page, 10)
    orders = await get_orders_by_status_and_range(pool, status, range_start, range_end, lim, off)
    total = await count_orders_by_status_and_range(pool, status, range_start, range_end)

    frm_iso, to_iso = date_from.isoformat(), date_to.isoformat()

    items = [
        (
            f"{o['id']}:{status}:{frm_iso}:{to_iso}:{page}",
            get_text("order_list_item_tpl", lang, LEXICON).format(
                daily_id=o["daily_id"],
                total=o["total_amount"],  # <<< TUZATISH: "so'm" bu yerdan olib tashlandi
            ),
        )
        for o in orders
    ]

    back_cb = "admin_view_orders"

    kb = build_pagination_keyboard(
        items_list=items,
        current_page=page,
        total_items=total,
        callback_prefix="view_order_details",
        lang=lang,
        back_callback_data=back_cb,
        page_callback=lambda p: f"orders_period_page:{status}:{frm_iso}:{to_iso}:{p}",
    )

    total_pages = max(1, ceil(total / 10))
    caption = f"{get_text('new_orders_list_title', lang, LEXICON)} ({page + 1}/{total_pages})"
    if not orders:
        caption = get_text("no_new_orders", lang, LEXICON)

    if isinstance(target, CallbackQuery):
        await target.answer()
        try:
            await target.message.edit_text(caption, reply_markup=kb)
        except TelegramBadRequest:
            await target.message.answer(caption, reply_markup=kb)
    else:
        await target.answer(caption, reply_markup=kb)


# ─── Buyurtmalarni sana bo'yicha filtrlash ───────────
@router.callback_query(F.data.startswith("view_orders_by_status:"))
async def cb_view_orders_by_status(call: CallbackQuery, pool: asyncpg.Pool):
    status = call.data.split(":", 1)[1]
    lang = _lang(await get_user(pool, call.from_user.id))
    # `build_date_gateway_menu` endi soddalashtirilgan
    kb = build_date_gateway_menu(lang, status)
    await call.message.edit_text(get_text("date_filter_title", lang, LEXICON), reply_markup=kb)
    await call.answer()


@router.callback_query(F.data.startswith("quick_date_select:"))
async def cb_quick_date_gateway(call: CallbackQuery, pool: asyncpg.Pool):
    status = call.data.split(":", 1)[1]
    lang = _lang(await get_user(pool, call.from_user.id))
    kb = build_quick_select_menu(lang, status)
    await call.message.edit_text(get_text("date_filter_title", lang, LEXICON), reply_markup=kb)
    await call.answer()


# ─── Kalendar FSM va yordamchi funksiyalari ───────────
class CalendarFSM(StatesGroup):
    choosing_date = State()


# handlers/admin_handlers.py

# Kalendar yorliqlari OS lokallariga bog'liq bo'lmasligi uchun shu yerda saqlanadi
# (Docker obrazida `locales` paketini o'rnatish shart emas).
_CALENDAR_LABELS: dict[str, tuple[list[str], list[str]]] = {
    "uz": (
        ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"],
        ["Yan", "Fev", "Mar", "Apr", "May", "Iyn", "Iyl", "Avg", "Sen", "Okt", "Noy", "Dek"],
    ),
    "ru": (
        ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"],
        ["Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"],
    ),
    "en": (
        ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"],
        ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    ),
}


def _make_calendar(lang: str) -> SimpleCalendar:
    """Lokalizatsiya qilingan kalendar obyektini yasaydi (OS lokallarisiz)."""
    calendar = SimpleCalendar()
    days, months = _CALENDAR_LABELS.get(lang, _CALENDAR_LABELS["en"])
    calendar._labels.days_of_week = days
    calendar._labels.months = months
    return calendar


# Eslatma: _patch_calendar_markup va _localize_calendar_buttons funksiyalari olib tashlandi.


@router.callback_query(F.data.startswith("select_specific_date:"))
async def cb_select_specific_date(call: CallbackQuery, state: FSMContext, pool: asyncpg.Pool):
    """Kalendarni ochadigan handler (tozalangan)."""
    status = call.data.split(":", 1)[1]
    await state.set_state(CalendarFSM.choosing_date)
    await state.update_data(status=status)

    lang = _lang(await get_user(pool, call.from_user.id))
    calendar = _make_calendar(lang)

    # Ortiqcha "patch" chaqiruvisiz
    markup = await calendar.start_calendar()

    await call.message.edit_text(get_text("date_filter_title", lang, LEXICON), reply_markup=markup)
    await call.answer()


@router.callback_query(SimpleCalendarCallback.filter(), CalendarFSM.choosing_date)
async def process_simple_calendar(
    call: CallbackQuery,
    callback_data: SimpleCalendarCallback,
    state: FSMContext,
    pool: asyncpg.Pool,
    settings: Settings,
):
    """Kalendar bilan barcha interaksiyalarni boshqaradi (yakuniy versiya)."""
    lang = _lang(await get_user(pool, call.from_user.id))
    calendar = _make_calendar(lang)
    selected, date_obj = await calendar.process_selection(call, callback_data)

    act = callback_data.act
    if act == "CANCEL":
        status = (await state.get_data()).get("status")
        await state.clear()
        kb = build_date_gateway_menu(lang, status)
        await call.message.edit_text(get_text("date_filter_title", lang, LEXICON), reply_markup=kb)
        await call.answer()
        return

    if selected:
        chosen_date = date_obj.date()
        status = (await state.get_data()).get("status")
        await state.clear()
        await show_orders_for_period(
            target=call,
            pool=pool,
            status=status,
            date_from=chosen_date,
            date_to=chosen_date + timedelta(days=1),
            page=0,
            tz=settings.tz,
        )


@router.callback_query(F.data.startswith("quick_date:"))
async def cb_quick_date(call: CallbackQuery, pool: asyncpg.Pool, settings: Settings):
    _, status, tag = call.data.split(":", 2)
    today = datetime.now(settings.tz).date()

    if tag == "today":
        frm = today
        to = today + timedelta(days=1)
    elif tag == "week":
        frm = today - timedelta(days=today.weekday())
        to = frm + timedelta(days=7)
    else:  # month
        frm = today.replace(day=1)
        to = frm.replace(year=frm.year + 1, month=1) if frm.month == 12 else frm.replace(month=frm.month + 1)
    await show_orders_for_period(call, pool, status, frm, to, page=0, tz=settings.tz)


@router.callback_query(F.data.startswith("orders_period_page:"))
async def cb_orders_period_page(call: CallbackQuery, pool: asyncpg.Pool, settings: Settings):
    try:
        _, status, frm_str, to_str, page_str = call.data.split(":", 4)
        page = int(page_str)
        frm = datetime.strptime(frm_str, "%Y-%m-%d").date()
        to = datetime.strptime(to_str, "%Y-%m-%d").date()
    except Exception:
        return await call.answer("Bad data", show_alert=True)
    await show_orders_for_period(call, pool, status, frm, to, page=page, tz=settings.tz)


@router.callback_query(F.data.startswith("orders_by_status_page:"))
async def cb_orders_by_status_page(call: CallbackQuery, pool: asyncpg.Pool):
    try:
        _, status, page_str = call.data.split(":", 2)
        page = int(page_str)
    except (ValueError, IndexError):
        return await call.answer("Invalid page", show_alert=True)
    await show_orders_by_status(call, pool, status, page=page)


def build_order_management_keyboard(order: asyncpg.Record, lang: str) -> InlineKeyboardMarkup:
    """Buyurtma holatiga qarab klaviaturani yasaydi (‘processing’ uchun kuryer tayinlash tugmasi bilan)."""
    rows = []
    status = order["status"]

    if status == "pending":
        rows.append(
            [
                InlineKeyboardButton(
                    text=get_text("accept_order_button", lang, LEXICON), callback_data=f"accept_order:{order['id']}"
                )
            ]
        )
    elif status == "processing":
        # oldingi “deliver_order” tugmasi o‘rniga yangi “assign_to_courier_btn” tugmasi
        rows.append(
            [
                InlineKeyboardButton(
                    text=get_text("assign_to_courier_btn", lang, LEXICON), callback_data=f"assign_courier:{order['id']}"
                )
            ]
        )
    elif status == "delivering":
        rows.append(
            [
                InlineKeyboardButton(
                    text=get_text("complete_order_button", lang, LEXICON), callback_data=f"complete_order:{order['id']}"
                )
            ]
        )

    # barcha holatlar uchun ortga qaytish
    rows.append(
        [
            InlineKeyboardButton(
                text=get_text("back_button", lang, LEXICON), callback_data=f"view_orders_by_status:{status}"
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data.startswith("assign_courier:"))
async def cb_assign_courier(call: CallbackQuery, pool: asyncpg.Pool):
    """
    ‘processing’ holatidagi buyurtma uchun mavjud kuryerlarni tanlash menyusini ko‘rsatadi.
    Endi har bir kuryerning real vaqt holatini (Busy/Free) ko‘rsatadi.
    """
    order_id = parse_int_arg(call.data)
    if order_id is None:
        return await call.answer()
    # Yangi yordamchi funksiyani chaqiramiz – bu barcha faol kuryerlarni va ularning hozirgi buyurtma sonini qaytaradi
    couriers = await get_couriers_with_status(pool)
    user = await get_user(pool, call.from_user.id)
    lang = _lang(user)

    if not couriers:
        # Agar kuryerlar yo‘q bo‘lsa, o‘sha xabarni ko‘rsatamiz
        await call.answer(get_text("no_available_couriers_alert", lang, LEXICON), show_alert=True)
        return

    buttons: list[list[InlineKeyboardButton]] = []
    for c in couriers:
        # Agar aktiv buyurtma mavjud bo‘lsa – Busy (🔴), aks holda Free (🟢)
        status_emoji = "🔴" if c["active_orders_count"] > 0 else "🟢"
        button_text = f"{status_emoji} {c['full_name']}"
        buttons.append(
            [InlineKeyboardButton(text=button_text, callback_data=f"confirm_assign:{order_id}:{c['user_id']}")]
        )

    # Orqaga qaytish tugmasi – o‘zgarmadi
    buttons.append(
        [
            InlineKeyboardButton(
                text=get_text("back_button", lang, LEXICON), callback_data=f"view_order_details:{order_id}"
            )
        ]
    )

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await call.message.edit_text(get_text("choose_courier_title", lang, LEXICON), reply_markup=kb)
    await call.answer()


# 3) “confirm_assign:” callback uchun handler
@router.callback_query(F.data.startswith("confirm_assign:"))
async def cb_confirm_assign(call: CallbackQuery, pool: asyncpg.Pool):
    """
    Tanlangan kuryerni buyurtmaga tayinlaydi va statusni yangilaydi,
    so‘ngra kuryer va mijozga xabar yuboradi.
    """
    user = await get_user(pool, call.from_user.id)
    lang = _lang(user)
    order_id = parse_int_arg(call.data, 1)
    courier_id = parse_int_arg(call.data, 2)
    if order_id is None or courier_id is None:
        return await call.answer(get_text("order_not_found_alert", lang, LEXICON), show_alert=True)

    # Atomik: faqat 'processing' holatidagi buyurtmaga va faqat faol kuryerni tayinlaydi
    if not await assign_courier_to_order(pool, order_id, courier_id):
        return await call.answer(get_text("order_status_conflict_alert", lang, LEXICON), show_alert=True)

    logger.info(
        "Courier assigned", extra={"order_id": order_id, "courier_id": courier_id, "by_admin": call.from_user.id}
    )
    await call.answer(get_text("courier_assigned_success_alert", lang, LEXICON), show_alert=True)

    order = await get_order(pool, order_id)
    courier_meta = await get_courier(pool, courier_id)

    # Kuryerga xabar
    courier_lang = _lang(await get_user(pool, courier_id))
    text_to_courier = get_text("new_delivery_for_courier_tpl", courier_lang, LEXICON).format(
        daily_id=order["daily_id"],
        customer_name=html.escape(order["customer_name"] or ""),
        customer_phone=html.escape(order["customer_phone"] or ""),
    )
    kb_courier = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_text("view_location_button", courier_lang, LEXICON),
                    url=f"https://www.google.com/maps?q={order['latitude']},{order['longitude']}",
                ),
                InlineKeyboardButton(
                    text=get_text("courier_confirm_delivery_button", courier_lang, LEXICON),
                    callback_data=f"deliver_confirm:{order_id}",
                ),
            ]
        ]
    )
    try:
        sent_message = await call.bot.send_message(courier_id, text_to_courier, reply_markup=kb_courier)
        # Keyinchalik tahrirlash uchun message_id ni saqlaymiz
        await save_courier_message_id(pool, order_id, sent_message.message_id)
    except Exception:
        logger.warning(
            "Failed to notify courier", extra={"order_id": order_id, "courier_id": courier_id}, exc_info=True
        )

    # Mijozga xabar
    customer_lang = _lang(await get_user(pool, order["user_id"]))
    text_to_customer = get_text("order_assigned_to_courier_for_customer_tpl", customer_lang, LEXICON).format(
        daily_id=order["daily_id"],
        courier_name=html.escape(courier_meta["full_name"]),
        courier_phone=html.escape(courier_meta["phone_number"] or ""),
    )
    try:
        await call.bot.send_message(order["user_id"], text_to_customer)
    except Exception:
        logger.warning("Failed to notify customer", extra={"order_id": order_id}, exc_info=True)

    await show_order_details(call, pool, order_id, answer=False)


async def show_order_details(
    call: CallbackQuery, pool: asyncpg.Pool, order_id: int, context: dict | None = None, *, answer: bool = True
):
    """
    Bitta buyurtma detallarini ko'rsatadigan MARKAZIY funksiya.
    Endi kuryer nomini ham, dinamik "Orqaga" tugmasini ham boshqaradi.
    """
    order = await pool.fetchrow("SELECT * FROM orders WHERE id = $1;", order_id)
    if not order:
        lang = _lang(await get_user(pool, call.from_user.id))
        await call.answer(get_text("order_not_found_alert", lang, LEXICON), show_alert=True)
        return

    user = await get_user(pool, call.from_user.id)
    lang = _lang(user)
    items = await get_order_items_with_names(pool, order_id)
    lines = [
        f"- {(json.loads(it['name']).get(lang) or next(iter(json.loads(it['name']).values())))} × {it['quantity']}"
        for it in items
    ]
    items_block = "\n".join(lines)

    text = get_text("order_details_tpl", lang, LEXICON).format(
        id=order["id"],
        daily_id=order["daily_id"],
        customer_label=get_text("customer_label", lang, LEXICON),
        name=html.escape(order["customer_name"] or ""),
        phone_label=get_text("phone_label", lang, LEXICON),
        phone=html.escape(order["customer_phone"] or ""),
        items_label=get_text("items_label", lang, LEXICON),
        items=items_block,
        status_label=get_text("status_label", lang, LEXICON),
        status=get_text(f"status_{order['status']}", lang, LEXICON),
        total=order["total_amount"],
    )

    # Kuryer nomini qo'shish mantig'i
    if order.get("courier_id"):
        courier_rec = await get_courier(pool, order["courier_id"])
        if courier_rec:
            courier_line = get_text("assigned_courier_info_tpl", lang, LEXICON).format(
                courier_name=courier_rec["full_name"]
            )
            text += f"\n\n{courier_line}"

    kb = build_order_management_keyboard(order, lang)

    # Dinamik "Orqaga" tugmasi mantig'i
    if context:
        dyn_back = InlineKeyboardButton(
            text=get_text("back_button", lang, LEXICON),
            callback_data=f"orders_period_page:{context['status']}:{context['frm']}:{context['to']}:{context['page']}",
        )
        # Klaviaturadagi oxirgi qatorni (standart "Orqaga" tugmasini) almashtiramiz
        kb.inline_keyboard[-1] = [dyn_back]

    # Xarita tugmasini qo'shish mantig'i
    if order.get("latitude") and order.get("longitude"):
        kb.inline_keyboard.insert(
            0,
            [
                InlineKeyboardButton(
                    text=get_text("location_button", lang, LEXICON),
                    url=f"https://www.google.com/maps?q={order['latitude']},{order['longitude']}",
                )
            ],
        )

    try:
        await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except TelegramBadRequest:
        pass  # Xabar o'zgarmagan bo'lsa, xatolikni e'tiborsiz qoldiramiz

    if answer:  # callback already answered with an alert by the caller
        await call.answer()


@router.callback_query(F.data == "get_daily_report")
async def cb_get_daily_report(call: CallbackQuery, pool: asyncpg.Pool, settings: Settings):
    """
    Kunlik hisobotni olish va pop-up oynada ko'rsatish.
    """
    # 1) Foydalanuvchi va tilni aniqlaymiz
    user = await get_user(pool, call.from_user.id)
    lang = _lang(user)

    # 2) Hisobot ma'lumotlarini olish
    day_start, day_end = local_day_bounds(datetime.now(settings.tz).date(), settings.tz)
    order_count, total_sum, best_seller = await get_daily_report(pool, day_start, day_end)

    # 3) Eng ko'p sotilgan mahsulot nomini lokalizatsiya qilish
    if best_seller:
        # best_seller — JSON string, tilga mos qiymatini olish
        names = json.loads(best_seller)
        best_seller_text = names.get(lang) or next(iter(names.values()))
    else:
        # Agar sotilgan mahsulot bo‘lmasa, placeholder
        best_seller_text = get_text("no_best_seller_label", lang, I18N)

    # 4) Xabarni shakllantiramiz va alert ko‘rinishida chiqaramiz
    report_msg = get_text("daily_report_tpl", lang, I18N).format(
        count=order_count, total_sum=total_sum, best_seller=best_seller_text
    )
    await call.answer(report_msg, show_alert=True)
