# utils/keyboards.py
import json
from collections.abc import Callable
from math import ceil

import asyncpg
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from locales.lexicon import LEXICON
from utils.lexicon_utils import get_text


def build_admin_main_menu(lang: str) -> InlineKeyboardMarkup:
    """Admin uchun asosiy boshqaruv menyusi."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=get_text("orders_button", lang, LEXICON), callback_data="admin_view_orders"),
                InlineKeyboardButton(
                    text=get_text("admin_manage_cats_btn", lang, LEXICON), callback_data="manage_categories"
                ),
            ],
            [InlineKeyboardButton(text=get_text("team_management_button", lang, LEXICON), callback_data="manage_team")],
            [
                InlineKeyboardButton(
                    text=get_text("settings_button", lang, LEXICON), callback_data="restaurant_settings"
                ),
            ],
            # Yangi tugma: kunlik hisobotni ko‘rsatish uchun
            [InlineKeyboardButton(text=get_text("daily_report_btn", lang, LEXICON), callback_data="get_daily_report")],
        ]
    )


def build_team_management_menu(lang: str) -> InlineKeyboardMarkup:
    """Jamoa boshqaruvi menyusi."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_text("manage_couriers_button", lang, LEXICON), callback_data="manage_couriers_btn"
                )
            ],
            [InlineKeyboardButton(text=get_text("back_button", lang, LEXICON), callback_data="admin_main_menu")],
        ]
    )


# utils/keyboards.py


def build_settings_menu(lang: str) -> InlineKeyboardMarkup:
    """Admin uchun sozlamalar menyusi (2 ustunli, balanslangan)."""
    back_callback = "admin_main_menu"

    keyboard = [
        [
            InlineKeyboardButton(
                text=get_text("language_settings_button", lang, LEXICON), callback_data="manage_languages"
            ),
            InlineKeyboardButton(text=get_text("manage_zone_btn", lang, LEXICON), callback_data="manage_zone"),
        ],
        [
            InlineKeyboardButton(text=get_text("set_work_hours_btn", lang, LEXICON), callback_data="set_work_hours"),
            # Bufer vaqtini ish vaqti yoniga qo'yamiz, mantiqan yaqin
            InlineKeyboardButton(
                text=get_text("set_order_buffer_btn", lang, LEXICON), callback_data="set_order_buffer"
            ),
        ],
        [
            InlineKeyboardButton(
                text=get_text("set_cancel_window_btn", lang, LEXICON), callback_data="set_cancel_window"
            ),
            InlineKeyboardButton(
                text=get_text("reset_daily_id_button", lang, LEXICON), callback_data="confirm_reset_daily_id"
            ),
        ],
        # Bu tugmani alohida qoldirgan ma'qul, chunki u tilni boshqarishga oid emas
        [
            InlineKeyboardButton(
                text=get_text("change_language_button", lang, LEXICON), callback_data="admin_change_language"
            )
        ],
        [InlineKeyboardButton(text=get_text("back_button", lang, LEXICON), callback_data=back_callback)],
    ]

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# Eslatma: build_team_management_menu funksiyasi olib tashlandi.
# Eslatma: build_courier_delivery_keyboard funksiyasi olib tashlandi.


# ==============================================================================
# Bu izohlar foydali bo'lgani uchun saqlab qolindi.
# QUYIDAGI FUNKSIYALAR SUPER ADMIN ROLI VA KO'P RESTORANLI TIZIM UCHUN
# KERAK BO'LGANLIGI SABABLI BUTUNLAY OLIB TASHALANDI:
# - build_super_admin_menu
# - build_tag_management_menu
# ==============================================================================


def build_orders_dashboard_keyboard(lang: str) -> InlineKeyboardMarkup:
    """
    Buyurtmalarni status bo'yicha ko'rish uchun menyu (faqat admin uchun soddalashtirilgan).
    """
    statuses = ("pending", "processing", "delivering", "completed", "canceled", "disputed")

    btn_list = [
        InlineKeyboardButton(text=get_text(f"status_{st}", lang, LEXICON), callback_data=f"view_orders_by_status:{st}")
        for st in statuses
    ]

    # Tugmalarni har qatorda 2 tadan joylashtirish
    rows = [btn_list[i : i + 2] for i in range(0, len(btn_list), 2)]

    # Orqaga qaytish tugmasi
    rows.append([InlineKeyboardButton(text=get_text("back_button", lang, LEXICON), callback_data="admin_main_menu")])

    return InlineKeyboardMarkup(inline_keyboard=rows)


# utils/keyboards.py fayli uchun tuzatish


def build_pagination_keyboard(
    items_list: list[tuple[int, str]],
    current_page: int,
    total_items: int,
    callback_prefix: str,
    lang: str,
    back_callback_data: str,
    *,
    page_callback: Callable[[int], str],
    max_items_per_page: int = 10,
) -> InlineKeyboardMarkup:
    """
    Har qanday ro'yxat uchun sahifalanadigan universal klaviatura yaratadi.

    ``items_list`` faqat JORIY sahifadagi elementlar bo'lishi kerak.
    ``page_callback(n)`` -> n-sahifa tugmasining callback_data'si. U majburiy:
    sahifa tugmasi ro'yxat kontekstini (kategoriya id va h.k.) o'zi bilishi kerak,
    aks holda (eski ``{prefix}_page:{n}`` kabi) uni hech bir handler tushunmaydi.
    """
    rows: list[list[InlineKeyboardButton]] = []

    # 1) Element tugmalari (har qatorga 2 tadan)
    for idx in range(0, len(items_list), 2):
        pair = items_list[idx : idx + 2]
        rows.append(
            [
                InlineKeyboardButton(
                    text=txt,
                    # TUZATILDI: callback_data ga endi sahifa raqami (current_page) ham qo'shilmoqda
                    callback_data=f"{callback_prefix}:{item_id}:{current_page}",
                )
                for item_id, txt in pair
            ]
        )

    # 2) Navigatsiya tugmalari (« »)
    total_pages = ceil(total_items / max_items_per_page) if total_items else 1
    nav_row: list[InlineKeyboardButton] = []
    if total_pages > 1:
        if current_page > 0:
            nav_row.append(InlineKeyboardButton(text="«", callback_data=page_callback(current_page - 1)))
        if current_page < total_pages - 1:
            nav_row.append(InlineKeyboardButton(text="»", callback_data=page_callback(current_page + 1)))
    if nav_row:
        rows.append(nav_row)

    # 3) "Orqaga" tugmasi
    rows.append([InlineKeyboardButton(text=get_text("back_button", lang, LEXICON), callback_data=back_callback_data)])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_date_selection_menu(lang: str, status: str) -> InlineKeyboardMarkup:
    """
    Buyurtmalarni sana bo'yicha filtrlash uchun menyu (soddalashtirilgan).
    """
    rows = [
        [
            InlineKeyboardButton(
                text=get_text("quick_select_button", lang, LEXICON), callback_data=f"select_specific_date:{status}"
            )
        ],
        [
            InlineKeyboardButton(
                text=get_text("specific_date_button", lang, LEXICON), callback_data=f"quick_date_select:{status}"
            )
        ],
        [
            InlineKeyboardButton(
                text=get_text("back_button", lang, LEXICON),
                # Endi bu menyudan faqat admin foydalanadi
                callback_data="admin_view_orders",
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ─── Sana gateway menyulari ───────────────────────────────────────────
def build_date_gateway_menu(lang: str, status: str) -> InlineKeyboardMarkup:
    """
    Buyurtmalarni sana bo'yicha filtrlash uchun menyu ("Tez tanlash" / "Aniq sana").
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_text("quick_select_button", lang, LEXICON), callback_data=f"quick_date_select:{status}"
                )
            ],
            [
                InlineKeyboardButton(
                    text=get_text("specific_date_button", lang, LEXICON), callback_data=f"select_specific_date:{status}"
                )
            ],
            [InlineKeyboardButton(text=get_text("back_button", lang, LEXICON), callback_data="admin_view_orders")],
        ]
    )


def build_quick_select_menu(lang: str, status: str) -> InlineKeyboardMarkup:
    """
    Sana bo'yicha tezkor tanlov menyusi (Bugun / Bu hafta / Bu oy).
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_text("quick_today_btn", lang, LEXICON), callback_data=f"quick_date:{status}:today"
                ),
                InlineKeyboardButton(
                    text=get_text("quick_week_btn", lang, LEXICON), callback_data=f"quick_date:{status}:week"
                ),
                InlineKeyboardButton(
                    text=get_text("quick_month_btn", lang, LEXICON), callback_data=f"quick_date:{status}:month"
                ),
            ],
            [
                InlineKeyboardButton(
                    text=get_text("back_button", lang, LEXICON), callback_data=f"view_orders_by_status:{status}"
                )
            ],
        ]
    )


# --- Mijozlar uchun menyular (o'zgarishsiz qoladi) ---


def build_customer_settings_menu(lang: str) -> InlineKeyboardMarkup:
    """
    Mijoz uchun sozlamalar menyusi.
    """
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=get_text("my_orders_button", lang, LEXICON), callback_data="my_orders")],
            [InlineKeyboardButton(text=get_text("my_addresses_button", lang, LEXICON), callback_data="my_addresses")],
            [
                InlineKeyboardButton(
                    text=get_text("change_language_button", lang, LEXICON), callback_data="change_language"
                )
            ],
            # <<< TUZATISH: "Hamkorlik" tugmasi vaqtinchalik olib tashlandi, "Orqaga" tugmasi to'g'ri ishlaydi
            [InlineKeyboardButton(text=get_text("back_button", lang, LEXICON), callback_data="go_to_main_menu")],
        ]
    )
    return kb


def build_addresses_list_keyboard(locations, lang: str) -> InlineKeyboardMarkup:
    """
    Mijozning saqlangan manzillari ro'yxatini ko'rsatish uchun klaviatura.
    """
    rows = [
        [
            InlineKeyboardButton(text=loc["name"], callback_data=f"select_saved_address:{loc['id']}"),
            InlineKeyboardButton(
                text=get_text("delete_address_button", lang, LEXICON), callback_data=f"delete_saved_address:{loc['id']}"
            ),
        ]
        for loc in locations
    ]
    rows.append(
        [InlineKeyboardButton(text=get_text("add_new_address_button", lang, LEXICON), callback_data="add_new_address")]
    )
    rows.append(
        [InlineKeyboardButton(text=get_text("back_button", lang, LEXICON), callback_data="customer_settings_menu")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_saved_address_menu(locations, lang: str) -> InlineKeyboardMarkup:
    """
    Saqlangan manzillarni tanlash uchun menyu.
    """
    rows = [
        [InlineKeyboardButton(text=loc["name"], callback_data=f"select_saved_address:{loc['id']}")] for loc in locations
    ]
    rows.append([InlineKeyboardButton(text=get_text("back_button", lang, LEXICON), callback_data="go_to_main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_main_menu_with_addresses(locations, lang: str) -> InlineKeyboardMarkup:
    """
    Asosiy menyuni saqlangan manzillar ro'yxati bilan birga ko'rsatish.
    """
    rows = [
        [InlineKeyboardButton(text=loc["name"], callback_data=f"select_saved_address:{loc['id']}")] for loc in locations
    ]
    rows.append(
        [InlineKeyboardButton(text=get_text("ask_for_location", lang, LEXICON), callback_data="go_to_location")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


# --- Tilni boshqarish menyusi (yangi) ---


def build_language_management_menu(languages: list, lang: str) -> InlineKeyboardMarkup:
    """Tillar ro'yxati va ularni o'zgartirish tugmalari bilan menyu yasaydi."""
    buttons = []
    for lang_rec in languages:
        status_icon = "✅" if lang_rec["is_enabled"] else "❌"
        button_text = f"{status_icon} {lang_rec['name']}"
        callback_data = f"toggle_lang:{lang_rec['code']}"
        buttons.append([InlineKeyboardButton(text=button_text, callback_data=callback_data)])

    buttons.append(
        [InlineKeyboardButton(text=get_text("back_button", lang, LEXICON), callback_data="restaurant_settings")]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_courier_panel_menu(lang: str) -> InlineKeyboardMarkup:
    """
    Kuryer paneli menyusi: “Faol yetkazib berishlarim” tugmasi.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_text("my_active_deliveries_button", lang, LEXICON), callback_data="my_active_deliveries"
                )
            ]
        ]
    )


def build_courier_details_menu(lang: str, courier_id: int) -> InlineKeyboardMarkup:
    """
    Kuriyer tafsilotlari ekranidan:
    – “Remove Courier”
    – “Back to list”
    tugmalarini beradi.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_text("remove_courier_btn", lang, LEXICON), callback_data=f"remove_courier:{courier_id}"
                )
            ],
            [InlineKeyboardButton(text=get_text("back_button", lang, LEXICON), callback_data="manage_couriers_btn")],
        ]
    )


def build_variation_list_keyboard(variations: list, product_id: int, lang: str) -> InlineKeyboardMarkup:
    """
    Mahsulotning mavjud variantlari ro'yxati uchun klaviatura.
    Endi har bir variantning holatini (sotuvda/emas) emoji bilan ko'rsatadi.
    """
    rows: list[list[InlineKeyboardButton]] = []

    # ➕ Yangi variant qo'shish tugmasi
    rows.append(
        [
            InlineKeyboardButton(
                text=get_text("add_variation_btn", lang, LEXICON), callback_data=f"add_variation:{product_id}"
            )
        ]
    )

    # Har bir variant uchun tugma
    for var in variations:
        # Holatiga qarab emoji tanlaymiz
        status_icon = "🟢" if var["is_available"] else "🔴"

        names = var["name"] if isinstance(var["name"], dict) else json.loads(var["name"])
        display_name = names.get(lang) or next(iter(names.values()))

        # Tugma matniga emoji qo'shamiz
        button_text = f"{status_icon} {display_name} - {var['price']}"

        rows.append([InlineKeyboardButton(text=button_text, callback_data=f"view_variation:{var['id']}")])

    # ⬅️ Orqaga — mahsulot menyusiga qaytish
    rows.append(
        [InlineKeyboardButton(text=get_text("back_button", lang, LEXICON), callback_data=f"product:{product_id}:0")]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_single_variation_menu(variation: asyncpg.Record, lang: str) -> InlineKeyboardMarkup:
    """
    Bitta variatsiya tafsilotlaridagi klaviatura.
    Endi tepada “Nomini tahrirlash” tugmasi bor va
    “Rasmni tahrirlash” tugmasi qo‘shildi.
    """
    var_id = variation["id"]
    prod_id = variation["product_id"]

    # 1) “Nomini tahrirlash” tugmasi (avvalgi)
    edit_name_btn = InlineKeyboardButton(
        text=get_text("edit_name_btn", lang, LEXICON), callback_data=f"edit_variation_name:{var_id}"
    )
    # 2) “Narxni tahrirlash” tugmasi (avvalgi)
    edit_price_btn = InlineKeyboardButton(
        text=get_text("edit_price_btn", lang, LEXICON), callback_data=f"edit_variation_price:{var_id}"
    )
    # === YANGI: “Rasmni tahrirlash” tugmasi ===
    edit_photo_btn = InlineKeyboardButton(
        text=get_text("edit_photo_btn", lang, LEXICON), callback_data=f"edit_variation_photo:{var_id}"
    )
    # 3) Mavjudlikni toggle qiluvchi tugma (avvalgi)
    if variation["is_available"]:
        avail_text = get_text("make_unavailable_btn", lang, LEXICON)
    else:
        avail_text = get_text("make_available_btn", lang, LEXICON)
    avail_btn = InlineKeyboardButton(text=avail_text, callback_data=f"toggle_variation_availability:{var_id}")
    # 4) O‘chirish tugmasi (avvalgi)
    del_btn = InlineKeyboardButton(
        text=get_text("delete_btn", lang, LEXICON), callback_data=f"confirm_delete_variation:{var_id}"
    )
    # 5) Orqaga tugmasi (avvalgi)
    back_btn = InlineKeyboardButton(
        text=get_text("back_button", lang, LEXICON), callback_data=f"manage_variations:{prod_id}"
    )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [edit_name_btn],
            [edit_price_btn],
            [edit_photo_btn],  # 🆕 bu yerda qo‘shildi
            [avail_btn],
            [del_btn],
            [back_btn],
        ]
    )


def build_quantity_keyboard(
    item_type: str,
    item_id: int,
    quantity: int,
    lang: str,
    category_id: int,
    page: int,
) -> InlineKeyboardMarkup:
    """
    Оддий маҳсулот учун миқдорни танлаш клавиатураси:
    ➖  [миқдор]  ➕
    📥 Саватга қўшиш
    ⬅️ Орқага (рўйхатга қайтиш)
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                # <<< TUZATISH: `text=` kalit so'zi qo'shildi
                InlineKeyboardButton(text="➖", callback_data=f"decr_qty:{item_type}:{item_id}"),
                # <<< TUZATISH: `text=` kalit so'zi qo'shildi
                InlineKeyboardButton(text=str(quantity), callback_data="noop"),
                # <<< TUZATISH: `text=` kalit so'zi qo'shildi
                InlineKeyboardButton(text="➕", callback_data=f"incr_qty:{item_type}:{item_id}"),
            ],
            [
                InlineKeyboardButton(
                    text=get_text("add_N_to_cart_btn", lang, LEXICON),
                    callback_data=f"add_N_to_cart:{item_type}:{item_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=get_text("back_button", lang, LEXICON),
                    callback_data=f"customer_back_to_cat:{category_id}:{page}",
                )
            ],
        ]
    )
