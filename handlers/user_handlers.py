# handlers/user_handlers.py
from datetime import UTC, datetime, timedelta

import asyncpg
from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
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
from db_helpers import (
    add_saved_location,
    add_user,
    delete_saved_location,
    get_cafe_settings,  # <-- til tanlovi uchun
    get_saved_location,
    get_saved_locations,
    get_user,
    set_user_role,
    update_user_first_name,
    update_user_location,
)
from handlers.customer_handlers import _lang, show_customer_category_content
from locales.lexicon import LEXICON
from utils.geo_utils import is_within_delivery_zone
from utils.geocoder import get_address_from_coords
from utils.keyboards import (
    build_addresses_list_keyboard,
    build_admin_main_menu,
    build_courier_panel_menu,
    build_main_menu_with_addresses,
)
from utils.lexicon_utils import get_text

router = Router(name="user")


# ==============================================================================
# QUYIDAGI FUNKSIYALAR KO'P RESTORANLI TIZIMDAGI "TEGLAR" (TAGS) MANTIG'I UCHUN
# KERAK BO'LGANLIGI SABABLI BUTUNLAY OLIB TASHALANDI:
#
# - show_tags_for_customer
# - cb_select_tag_page
#
# Yagona kafe tizimida mijoz to'g'ridan-to'g'ri menyuga (kategoriyalarga)
# o'tishi kerak, teg tanlash bosqichi endi keraksiz.
# ==============================================================================


# Eslatma: `show_staff_main_menu` va `show_staff_panel` funksiyalari olib tashlandi.


@router.callback_query(F.data == "go_to_main_menu")
async def cb_go_to_main_menu(call: CallbackQuery, state: FSMContext, pool: asyncpg.Pool):
    """
    "Orqaga" tugmasi uchun soddalashtirilgan handler.
    Bu endi qaytadan lokatsiya so'ramaydi, shunchaki asosiy menyuni ko'rsatadi.
    """
    # show_customer_category_content funksiyasini chaqiramiz (u customer_handlers.py da)
    text, kb = await show_customer_category_content(call, pool, category_id=None, current_page=0, parent_page=0)
    try:
        await call.message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        # Xabar o'zgarmagan bo'lsa, xatolik berishi mumkin. E'tiborsiz qoldiramiz.
        pass
    await call.answer()


class CustomerLocationFSM(StatesGroup):
    """Mijoz lokatsiyasini olish uchun FSM holatlari."""

    waiting_for_main_location = State()
    waiting_for_address_confirmation = State()


# ------------------------ /start (Soddalashtirilgan) ---------------------------
@router.message(Command("start"))
async def cmd_start(
    message: Message,
    state: FSMContext,
    pool: asyncpg.Pool,
    settings: Settings,
) -> None:
    """
    /start buyrug‘i kelganda ishlaydi.
    1) Foydalanuvchini ro‘yxatlash yoki yangilash
    2) Agar admin bo‘lsa → admin menyusi
    3) Agar courier bo‘lsa → courier paneli
    4) Aks holda → mijoz logikasi (joylashuv va kategoriyalar)
    """
    # FSM holatini tozalaymiz
    await state.clear()
    tg_user = message.from_user

    # --- 1) DBda foydalanuvchini olish yoki yaratish ---
    db_user = await get_user(pool, tg_user.id)
    if not db_user:
        await add_user(
            pool, tg_user.id, tg_user.first_name or "NoName", tg_user.username, tg_user.language_code or "uz"
        )
        db_user = await get_user(pool, tg_user.id)

    # Agar Telegramdagi ismi o‘zgarib qolgan bo‘lsa, yangilaymiz
    if db_user["first_name"] != (tg_user.first_name or "NoName"):
        await update_user_first_name(pool, tg_user.id, tg_user.first_name or "NoName")

    # Tanlangan tilni aniqlaymiz
    lang = db_user.get("selected_language_code") or db_user.get("language_code") or "uz"

    # --- 2) Admin bo‘lsa, admin menyusini ko‘rsatamiz ---
    if settings.is_admin(tg_user.id):
        if db_user.get("role") != "admin":
            # Rol admin emas edi, endi admin qilib o‘rnatamiz
            await set_user_role(pool, tg_user.id, "admin")

        await message.answer(get_text("admin_welcome", lang, LEXICON), reply_markup=build_admin_main_menu(lang))
        return

    # --- 3) Courier bo‘lsa, courier panelini ko‘rsatamiz ---
    elif db_user.get("role") == "courier":
        await message.answer(
            get_text("courier_panel_title", lang, LEXICON), reply_markup=build_courier_panel_menu(lang)
        )
        return

    # --- 4) Aks holda — mijoz flow ---
    # Café sozlamalarini olamiz
    cafe_settings = await get_cafe_settings(pool)

    # 4.1) Agar zonani hali belgilamagan bo‘lsak — eski location/kategoriya logikasi
    if cafe_settings.get("latitude") is None:
        # 24 soat ichida yangilangan location bo‘lsa, keshdan foydalanamiz
        if (
            db_user["last_known_latitude"] is not None
            and db_user["location_last_updated_at"] is not None
            and datetime.now(UTC) - db_user["location_last_updated_at"] < timedelta(hours=24)
        ):
            await state.update_data(
                session_lat=db_user["last_known_latitude"], session_lon=db_user["last_known_longitude"]
            )
            text, kb = await show_customer_category_content(message, pool, None, 0)
            await message.answer(text, reply_markup=kb)
            return

        # Aks holda — saqlangan manzillarni taklif yoki yangi location so‘rov
        locs = await get_saved_locations(pool, tg_user.id)
        if locs:
            kb = build_main_menu_with_addresses(locs, lang)
            await message.answer(get_text("ask_for_location", lang, LEXICON), reply_markup=kb)
        else:
            kb = ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text=get_text("ask_for_location", lang, LEXICON), request_location=True)]],
                resize_keyboard=True,
                one_time_keyboard=True,
            )
            await state.set_state(CustomerLocationFSM.waiting_for_main_location)
            await message.answer(get_text("ask_for_location", lang, LEXICON), reply_markup=kb)
        return

    # 4.2) Agar zonani belgilagan bo‘lsak — har doim location so‘raymiz
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=get_text("ask_for_location", lang, LEXICON), request_location=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await state.set_state(CustomerLocationFSM.waiting_for_main_location)
    await message.answer(get_text("ask_for_location", lang, LEXICON), reply_markup=kb)


@router.callback_query(F.data.in_({"request_location_again", "go_to_location"}))
async def cb_request_location_again(call: CallbackQuery, state: FSMContext, pool: asyncpg.Pool):
    """
    Foydalanuvchidan hech qanday keshlangan ma'lumotni tekshirmasdan,
    to'g'ridan-to'g'ri lokatsiya so'raydi.
    """
    user = await get_user(pool, call.from_user.id)
    lang = user.get("selected_language_code") or user.get("language_code") or "uz"

    # Lokatsiya so'rash uchun klaviatura
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=get_text("ask_for_location", lang, LEXICON), request_location=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    # Holatni o'rnatamiz, bot lokatsiya kutayotganini bilishi uchun
    await state.set_state(CustomerLocationFSM.waiting_for_main_location)

    # Eski xabarni o'chirib, yangi so'rov yuboramiz
    await call.message.delete()
    await call.message.answer(get_text("ask_for_location", lang, LEXICON), reply_markup=kb)
    await call.answer()


# ==============================================================================
# QUYIDAGI FUNKSIYALAR KO'P RESTORANLI TIZIMDAGI "TEGLAR" VA "RESTORANLAR
# RO'YXATI" MANTIG'I UCHUN KERAK BO'LGANLIGI SABABLI BUTUNLAY OLIB TASHALANDI:
#
# - back_to_rest_list
# - cb_customer_tags_page
# - cb_select_tag
#
# Yagona kafe tizimida bu funksiyalarga ehtiyoj yo'q.
# ==============================================================================


@router.message(CustomerLocationFSM.waiting_for_main_location, F.location)
async def process_customer_location(
    message: Message,
    state: FSMContext,
    pool: asyncpg.Pool,
):
    """
    Foydalanuvchi lokatsiya yuborganda ishlaydi. Bu funksiya o'zgarishsiz qoldirildi.
    """
    lat, lon = message.location.latitude, message.location.longitude

    address = await get_address_from_coords(lat, lon)
    user = await get_user(pool, message.from_user.id)
    lang = user.get("selected_language_code") or user.get("language_code") or "uz"
    await state.update_data(tmp_lat=lat, tmp_lon=lon)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_text("confirm_address_yes", lang, LEXICON), callback_data=f"confirm_address:{lat}:{lon}"
                ),
                InlineKeyboardButton(text=get_text("reenter_location", lang, LEXICON), callback_data="go_to_main_menu"),
            ]
        ]
    )
    await message.answer(
        get_text("address_confirmation_tpl", lang, LEXICON).format(address=address or "Manzil topilmadi"),
        reply_markup=kb,
    )
    await state.set_state(CustomerLocationFSM.waiting_for_address_confirmation)


@router.callback_query(F.data.startswith("confirm_address:"))
async def cb_confirm_address(call: CallbackQuery, state: FSMContext, pool: asyncpg.Pool):
    try:
        _, lat_str, lon_str = call.data.split(":")
        lat, lon = float(lat_str), float(lon_str)
    except ValueError:
        return await call.answer()
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return await call.answer()

    # Lokatsiyani bazaga va sessiyaga saqlash
    await update_user_location(pool, call.from_user.id, lat, lon)
    await state.update_data(session_lat=lat, session_lon=lon)

    # Café sozlamalarini va foydalanuvchi tilini olish
    cafe_settings = await get_cafe_settings(pool)
    user = await get_user(pool, call.from_user.id)
    lang = user.get("selected_language_code") or user.get("language_code") or "uz"

    # Agar admin umuman lokatsiya belgilamagan bo'lsa, tekshiruv shart emas
    if cafe_settings.get("latitude") is None:
        await state.update_data(out_of_zone=False)  # Har ehtimolga qarshi
        text, kb = await show_customer_category_content(call, pool, None, 0)
        try:
            await call.message.edit_text(text, reply_markup=kb)
        except TelegramBadRequest:
            pass  # Xabar o'zgarmagan bo'lsa, xatolik beradi
        await call.answer()
        return

    # Agar radius belgilangan va lokatsiya zonadan tashqarida bo'lsa:
    if not is_within_delivery_zone(cafe_settings, lat, lon):
        # FSMga foydalanuvchi "zona tashqarisida" ekanligini yozamiz
        await state.update_data(out_of_zone=True)

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=get_text("reenter_location_button", lang, LEXICON), callback_data="request_location_again"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=get_text("settings_button", lang, LEXICON), callback_data="customer_settings_menu"
                    )
                ],
            ]
        )
        await call.message.edit_text(get_text("no_restaurants_delivery_area", lang, LEXICON), reply_markup=kb)
        await call.answer()
        return

    # Aks holda, foydalanuvchi zona ichida
    # FSMga foydalanuvchi "zona ichida" ekanligini yozamiz
    await state.update_data(out_of_zone=False)
    text, kb = await show_customer_category_content(call, pool, None, 0)
    try:
        await call.message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        pass
    await call.answer()


class AddSavedAddressFSM(StatesGroup):
    # Bu FSM holatlari o'zgarishsiz qoldirildi.
    waiting_for_location = State()
    waiting_for_name = State()


@router.callback_query(F.data == "my_addresses")
async def cb_my_addresses(call: CallbackQuery, state: FSMContext, pool: asyncpg.Pool):
    # Bu funksiya o'zgarishsiz qoldirildi.
    user_id = call.from_user.id
    user = await get_user(pool, user_id)
    lang = user.get("selected_language_code") or user.get("language_code") or "uz"
    locs = await get_saved_locations(pool, user_id)

    if not locs:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=get_text("add_new_address_button", lang, LEXICON), callback_data="add_new_address"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=get_text("back_button", lang, LEXICON), callback_data="customer_settings_menu"
                    )
                ],
            ]
        )
        await call.message.edit_text(get_text("no_saved_addresses", lang, LEXICON), reply_markup=kb)
    else:
        kb = build_addresses_list_keyboard(locs, lang)
        await call.message.edit_text(get_text("address_list_title", lang, LEXICON), reply_markup=kb)

    await call.answer()


@router.callback_query(F.data == "add_new_address")
async def cb_add_new_address(call: CallbackQuery, state: FSMContext, pool: asyncpg.Pool):
    # Bu funksiya o'zgarishsiz qoldirildi.
    user = await get_user(pool, call.from_user.id)
    lang = user.get("selected_language_code") or user.get("language_code") or "uz"

    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=get_text("ask_for_address_location", lang, LEXICON), request_location=True)]],
        resize_keyboard=True,
    )
    await call.message.answer(get_text("ask_for_address_location", lang, LEXICON), reply_markup=kb)
    await state.set_state(AddSavedAddressFSM.waiting_for_location)
    await call.answer()


@router.message(AddSavedAddressFSM.waiting_for_location, F.location)
async def fsm_saved_loc_receive(message: Message, state: FSMContext, pool: asyncpg.Pool):
    """
    Saqlanayotgan manzilning lokatsiyasini qabul qiladi.
    Ikki marta e'lon qilingan funksiya bittaga birlashtirildi.
    """
    await state.update_data(
        tmp_lat=message.location.latitude,
        tmp_lon=message.location.longitude,
    )

    user = await get_user(pool, message.from_user.id)
    lang = user.get("selected_language_code") or user.get("language_code") or "uz"

    await message.answer(get_text("ask_for_address_name", lang, LEXICON), reply_markup=ReplyKeyboardRemove())
    await state.set_state(AddSavedAddressFSM.waiting_for_name)


@router.message(AddSavedAddressFSM.waiting_for_name, F.text)
async def fsm_saved_loc_name(message: Message, state: FSMContext, pool: asyncpg.Pool):
    """
    Saqlanayotgan manzil nomini qabul qilib, bazaga yozadi. O'zgarishsiz qoldirildi.
    """
    data = await state.get_data()
    name = message.text.strip()
    lat, lon = data["tmp_lat"], data["tmp_lon"]

    address = await get_address_from_coords(lat, lon)

    await add_saved_location(pool, message.from_user.id, name, lat, lon, address)

    user = await get_user(pool, message.from_user.id)
    lang = user.get("selected_language_code") or user.get("language_code") or "uz"
    await message.answer(get_text("address_saved_success", lang, LEXICON))

    locs = await get_saved_locations(pool, message.from_user.id)
    kb = build_addresses_list_keyboard(locs, lang)
    await message.answer(get_text("address_list_title", lang, LEXICON), reply_markup=kb)

    await state.clear()


@router.callback_query(F.data.startswith("delete_saved_address:"))
async def cb_delete_saved_address(call: CallbackQuery, state: FSMContext, pool: asyncpg.Pool):
    """Saqlangan manzilni o'chirish. O'zgarishsiz qoldirildi."""
    _, loc_id_str = call.data.split(":")
    loc_id = int(loc_id_str)
    user_id = call.from_user.id

    await delete_saved_location(pool, loc_id, user_id)

    user = await get_user(pool, user_id)
    lang = user.get("selected_language_code") or user.get("language_code") or "uz"
    await call.answer(get_text("address_deleted_success", lang, LEXICON), show_alert=True)

    await cb_my_addresses(call, state, pool)


@router.callback_query(F.data.startswith("select_saved_address:"))
async def cb_select_saved_address(
    call: CallbackQuery,
    pool: asyncpg.Pool,
    state: FSMContext,
):
    """Saqlangan manzil tanlanganda ishlaydi va uni sessiya xotirasiga saqlaydi."""
    loc_id = int(call.data.split(":", 1)[1])
    rec = await get_saved_location(pool, loc_id, call.from_user.id)

    # Agar biror sabab bilan manzil bazadan topilmasa, foydalanuvchiga xabar beramiz
    if not rec:
        user = await get_user(pool, call.from_user.id)
        lang = _lang(user)
        await call.answer(get_text("address_not_found", lang, LEXICON), show_alert=True)
        return

    # YECHIM: Topilgan joylashuvni FSM xotirasiga joriy sessiya uchun saqlaymiz
    await state.update_data(session_lat=rec["latitude"], session_lon=rec["longitude"])

    # Asosiy menyuni (kategoriyalar ro'yxatini) ko'rsatamiz
    text, kb = await show_customer_category_content(call, pool, category_id=None, current_page=0)
    try:
        await call.message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        await call.message.answer(text, reply_markup=kb)
    await call.answer()
