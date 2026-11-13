# db_helpers.py
"""
Maʼlumotlar bazasi bilan ishlash uchun yordamchi funksiyalar (asyncpg).
"""

import json
from collections.abc import Collection, Iterable, Mapping
from datetime import UTC, datetime, time
from decimal import Decimal
from typing import Any

import asyncpg

ADMIN_ROLE = "admin"
COURIER_ROLE = "courier"
CUSTOMER_ROLE = "customer"


async def get_user(pool: asyncpg.Pool, user_id: int) -> asyncpg.Record | None:
    """ID bo'yicha foydalanuvchi ma'lumotlarini to'liq qaytaradi."""
    query = "SELECT * FROM users WHERE id = $1;"
    async with pool.acquire() as conn:
        return await conn.fetchrow(query, user_id)


async def add_user(
    pool: asyncpg.Pool,
    user_id: int,
    first_name: str = "NoName",
    username: str | None = None,
    language_code: str | None = None,
    role: str = "customer",
) -> None:
    """
    Yangi foydalanuvchini bazaga qo'shadi.
    selected_language_code standarti 'uz' ga o'rnatiladi.
    """
    query = """
        INSERT INTO users
            (id, first_name, username, language_code, selected_language_code, role)
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (id) DO NOTHING;
    """
    async with pool.acquire() as conn:
        await conn.execute(
            query,
            user_id,
            first_name,
            username,
            language_code,
            "uz",  # default til
            role,
        )


async def ensure_user(
    pool: asyncpg.Pool,
    user_id: int,
    first_name: str | None,
    username: str | None,
    language_code: str | None,
    *,
    is_admin: bool,
) -> asyncpg.Record:
    """
    Foydalanuvchini bazada borligini kafolatlaydi va admin rolini konfiguratsiya
    (ADMIN_IDS) bilan sinxronlaydi. Faqat o'zgarish bo'lsagina yozadi.

    * ADMIN_IDS ichida bo'lsa → role = 'admin'
    * ADMIN_IDS dan olib tashlangan sobiq admin → 'courier' (faol kuryer bo'lsa) yoki 'customer'
    """
    first_name = first_name or "NoName"
    user = await get_user(pool, user_id)
    if user is None:
        await add_user(
            pool,
            user_id,
            first_name,
            username,
            language_code or "uz",
            role=ADMIN_ROLE if is_admin else CUSTOMER_ROLE,
        )
        return await get_user(pool, user_id)

    role = user["role"]
    if is_admin:
        new_role = ADMIN_ROLE
    elif role == ADMIN_ROLE:
        courier = await get_courier(pool, user_id)
        new_role = COURIER_ROLE if courier and courier["is_active"] else CUSTOMER_ROLE
    else:
        new_role = role

    if new_role != role or user["first_name"] != first_name or user["username"] != username:
        return await pool.fetchrow(
            "UPDATE users SET role = $2, first_name = $3, username = $4 WHERE id = $1 RETURNING *;",
            user_id,
            new_role,
            first_name,
            username,
        )
    return user


async def set_user_role(
    pool: asyncpg.Pool,
    user_id: int,
    role: str,
) -> None:
    """
    Foydalanuvchining rolini o'zgartiradi.
    'restaurant_id' olib tashlandi.
    """
    query = """
        UPDATE users
        SET role = $2
        WHERE id = $1;
    """
    async with pool.acquire() as conn:
        await conn.execute(query, user_id, role)


async def set_user_selected_language(
    pool: asyncpg.Pool,
    user_id: int,
    lang_code: str,
) -> None:
    """Foydalanuvchining tanlagan tilini ma'lumotlar bazasida saqlaydi."""
    query = """
        UPDATE users
        SET selected_language_code = $2
        WHERE id = $1;
    """
    async with pool.acquire() as conn:
        await conn.execute(query, user_id, lang_code)


async def add_category(
    pool: asyncpg.Pool,
    name_jsonb: Mapping[str, str],
    parent_id: int | None = None,
) -> int:
    """
    Yangi kategoriya qo'shadi. 'restaurant_id' olib tashlandi.
    """
    names_str = json.dumps(name_jsonb)
    query = """
        INSERT INTO categories (parent_id, name)
        VALUES ($1, $2)
        RETURNING id;
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, parent_id, names_str)
        return row["id"]


async def get_toplevel_categories(
    pool: asyncpg.Pool,
    offset: int | None = None,
    limit: int | None = None,
):
    """
    Eng yuqori darajadagi (asosiy) kategoriyalarni qaytaradi.
    'restaurant_id' bo'yicha filtrlash olib tashlandi.
    """
    base_sql = """
        SELECT * FROM categories
        WHERE parent_id IS NULL
          AND is_active = TRUE
        ORDER BY id
    """
    if offset is not None and limit is not None:
        base_sql += " LIMIT $1 OFFSET $2;"
        params = (limit, offset)
    else:
        base_sql += ";"
        params = ()  # Parametrlar yo'q
    async with pool.acquire() as conn:
        return await conn.fetch(base_sql, *params)


async def get_subcategories(
    pool: asyncpg.Pool,
    parent_id: int,
    offset: int | None = None,
    limit: int | None = None,
):
    """
    Ichki kategoriyalarni (sub-kategoriyalarni) qaytaradi.
    Bu funksiya o'zgarishsiz qoldi, chunki u 'restaurant_id' ga bog'liq emas.
    """
    sql = """
        SELECT * FROM categories
        WHERE parent_id = $1
          AND is_active = TRUE
        ORDER BY id
    """
    params: tuple = (parent_id,)
    if offset is not None and limit is not None:
        sql += " LIMIT $2 OFFSET $3;"
        params = (parent_id, limit, offset)
    else:
        sql += ";"
    async with pool.acquire() as conn:
        return await conn.fetch(sql, *params)


async def get_product(pool: asyncpg.Pool, product_id: int):
    """
    ID bo'yicha mahsulot ma'lumotlarini qaytaradi. O'zgarishsiz qoldi.
    """
    query = "SELECT * FROM products WHERE id = $1;"
    async with pool.acquire() as conn:
        return await conn.fetchrow(query, product_id)


async def get_products_in_category(
    pool: asyncpg.Pool,
    category_id: int,
    offset: int | None = None,
    limit: int | None = None,
):
    """
    Berilgan kategoriyadagi mahsulotlarni sahifalab qaytaradi.
    """
    sql = """
        SELECT * FROM products
        WHERE category_id = $1
          AND is_available = TRUE
        ORDER BY id
    """
    params: tuple[Any, ...]
    if offset is not None and limit is not None:
        sql += " LIMIT $2 OFFSET $3;"
        params = (category_id, limit, offset)
    else:
        sql += ";"
        params = (category_id,)
    async with pool.acquire() as conn:
        return await conn.fetch(sql, *params)


async def count_products_in_category(pool: asyncpg.Pool, category_id: int) -> int:
    """
    Kategoriyadagi mavjud mahsulotlar sonini sanaydi.
    """
    sql = """
        SELECT COUNT(*) FROM products
        WHERE category_id = $1
          AND is_available = TRUE;
    """
    async with pool.acquire() as conn:
        return await conn.fetchval(sql, category_id)


async def update_product_price(pool: asyncpg.Pool, product_id: int, new_price: float):
    """Mahsulot narxini yangilaydi."""
    query = "UPDATE products SET price = $2 WHERE id = $1;"
    async with pool.acquire() as conn:
        await conn.execute(query, product_id, new_price)


async def update_product_name(pool, product_id: int, new_name_jsonb: Mapping[str, str]):
    """Mahsulot nomini yangilaydi."""
    name_str = json.dumps(new_name_jsonb)
    query = "UPDATE products SET name = $2 WHERE id = $1;"
    async with pool.acquire() as conn:
        await conn.execute(query, product_id, name_str)


async def update_product_photo(pool, product_id: int, new_photo_file_id: str):
    """Mahsulot rasmini yangilaydi."""
    query = "UPDATE products SET photo_file_id = $2 WHERE id = $1;"
    async with pool.acquire() as conn:
        await conn.execute(query, product_id, new_photo_file_id)


async def update_product_description(
    pool,
    product_id: int,
    new_desc_jsonb: Mapping[str, str],
):
    """Mahsulot tavsifini yangilaydi."""
    desc_str = json.dumps(new_desc_jsonb)
    query = "UPDATE products SET description = $2 WHERE id = $1;"
    async with pool.acquire() as conn:
        await conn.execute(query, product_id, desc_str)


async def add_product(
    pool: asyncpg.Pool,
    category_id: int,
    name_jsonb: Mapping[str, str],
    description_jsonb: Mapping[str, str],
    photo_file_id: str,
    price: float,
) -> int:
    """
    Yangi mahsulot qo'shadi.
    """
    name_str = json.dumps(name_jsonb)
    desc_str = json.dumps(description_jsonb)
    query = """
        INSERT INTO products
        (category_id, name, description, photo_file_id, price)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id;
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, category_id, name_str, desc_str, photo_file_id, price)
        return row["id"]


async def get_products_by_category(pool: asyncpg.Pool, category_id: int):
    """
    Berilgan kategoriya uchun mahsulotlar ro‘yxatini qaytaradi.
    """
    query = """
        SELECT * FROM products
        WHERE category_id = $1
        ORDER BY id;
    """
    async with pool.acquire() as conn:
        return await conn.fetch(query, category_id)


async def get_category(pool: asyncpg.Pool, category_id: int) -> asyncpg.Record | None:
    """ID bo'yicha kategoriya ma'lumotini qaytaradi."""
    query = "SELECT * FROM categories WHERE id = $1;"
    async with pool.acquire() as conn:
        return await conn.fetchrow(query, category_id)


async def update_category_name(
    pool: asyncpg.Pool,
    category_id: int,
    new_name_jsonb: Mapping[str, str],
) -> None:
    """Kategoriya nomini yangilaydi."""
    new_name_str = json.dumps(new_name_jsonb)
    query = "UPDATE categories SET name = $2 WHERE id = $1;"
    async with pool.acquire() as conn:
        await conn.execute(query, category_id, new_name_str)


async def create_order(
    pool: asyncpg.Pool,
    user_id: int,
    final_order_details: list[dict],
    total_amount: Decimal,
    phone: str,
    latitude: float | None,
    longitude: float | None,
    customer_name: str,
) -> tuple[int, int]:
    """
    Inserts a new order and its items.  Refactored to consume
    final_order_details entries of the form:
      {
        'product_id': int,
        'variation_id': int | None,
        'quantity': int,
        'price_per_item': Decimal
      }
    Returns: (order_id, new_daily_id)
    """
    async with pool.acquire() as conn, conn.transaction():
        # Atomik hisoblagich: UPDATE qatorni qulflaydi, shuning uchun bir vaqtda
        # yaratilgan buyurtmalar hech qachon bir xil daily_id olmaydi.
        new_daily_id = await conn.fetchval(
            "INSERT INTO order_counter (id, last_value) VALUES (1, 1) "
            "ON CONFLICT (id) DO UPDATE SET last_value = order_counter.last_value + 1 "
            "RETURNING last_value;"
        )

        # main order row
        row = await conn.fetchrow(
            """
                INSERT INTO orders
                  (daily_id, user_id, total_amount, status,
                   customer_phone, customer_name, latitude, longitude)
                VALUES ($1, $2, $3, 'pending', $4, $5, $6, $7)
                RETURNING id;
                """,
            new_daily_id,
            user_id,
            total_amount,
            phone,
            customer_name,
            latitude,
            longitude,
        )
        order_id = row["id"]

        # insert each line item, now honoring variation_id (NULL if simple product)
        insert_sql = """
                INSERT INTO order_items
                  (order_id, product_id, variation_id, quantity, price_per_item)
                VALUES ($1, $2, $3, $4, $5);
            """
        for item in final_order_details:
            await conn.execute(
                insert_sql,
                order_id,
                item["product_id"],
                item["variation_id"],
                item["quantity"],
                item["price_per_item"],
            )

        return order_id, new_daily_id


async def get_orders_by_status(pool: asyncpg.Pool, status: str):
    """
    Status bo'yicha buyurtmalarni oladi.
    """
    query = """
        SELECT id, total_amount, created_at
        FROM orders
        WHERE status = $1
        ORDER BY created_at;
    """
    async with pool.acquire() as conn:
        return await conn.fetch(query, status)


async def update_user_first_name(pool: asyncpg.Pool, user_id: int, new_name: str) -> None:
    """Foydalanuvchi ismini yangilaydi."""
    query = "UPDATE users SET first_name = $2 WHERE id = $1;"
    async with pool.acquire() as conn:
        await conn.execute(query, user_id, new_name)


async def get_order_items_with_names(pool: asyncpg.Pool, order_id: int):
    """
    Buyurtma ID si bo‘yicha mahsulotlar (nomi, miqdori, narxi) ro‘yxatini qaytaradi.
    """
    query = """
        SELECT p.name, oi.quantity, oi.price_per_item
        FROM order_items oi
        JOIN products p ON p.id = oi.product_id
        WHERE oi.order_id = $1;
    """
    async with pool.acquire() as conn:
        return await conn.fetch(query, order_id)


async def update_order_status(pool: asyncpg.Pool, order_id: int, new_status: str):
    """Buyurtma holatini shartsiz yangilaydi (faqat ichki/test maqsadlarda)."""
    query = "UPDATE orders SET status = $2, updated_at = CURRENT_TIMESTAMP WHERE id = $1;"
    async with pool.acquire() as conn:
        await conn.execute(query, order_id, new_status)


# Ruxsat etilgan holat o'tishlari (buyurtmaning hayot sikli)
ORDER_TRANSITIONS: dict[str, frozenset[str]] = {
    "pending": frozenset({"processing", "canceled"}),
    "processing": frozenset({"delivering", "canceled"}),
    "delivering": frozenset({"completed", "disputed"}),
    "disputed": frozenset({"completed"}),
    "completed": frozenset(),
    "canceled": frozenset(),
}


def can_transition(from_status: str, to_status: str) -> bool:
    return to_status in ORDER_TRANSITIONS.get(from_status, frozenset())


async def transition_order_status(
    pool: asyncpg.Pool,
    order_id: int,
    *,
    from_statuses: Iterable[str],
    to_status: str,
    user_id: int | None = None,
    courier_id: int | None = None,
    created_after: datetime | None = None,
) -> asyncpg.Record | None:
    """
    Buyurtma holatini ATOMIK o'zgartiradi: faqat joriy holat ``from_statuses``
    ichida bo'lsa (va berilgan bo'lsa, buyurtma shu mijoz/kuryerga tegishli bo'lsa).

    Muvaffaqiyatli bo'lsa yangilangan qatorni, aks holda ``None`` qaytaradi —
    shu tariqa ikki marta bosish yoki soxta callback holatni buzolmaydi.
    """
    from_statuses = list(from_statuses)
    allowed = [s for s in from_statuses if can_transition(s, to_status)]
    if not allowed:
        raise ValueError(f"No valid transition into {to_status!r} from {from_statuses!r}")
    query = """
        UPDATE orders
           SET status = $2, updated_at = CURRENT_TIMESTAMP
         WHERE id = $1
           AND status = ANY($3::text[])
           AND ($4::bigint IS NULL OR user_id = $4)
           AND ($5::bigint IS NULL OR courier_id = $5)
           AND ($6::timestamptz IS NULL OR created_at >= $6)
     RETURNING *;
    """
    return await pool.fetchrow(query, order_id, to_status, allowed, user_id, courier_id, created_after)


async def get_user_orders(pool: asyncpg.Pool, user_id: int):
    """
    Foydalanuvchining barcha buyurtmalarini qaytaradi. (YANGILANGAN)
    """
    # <<< O'ZGARISH: SELECT so'roviga `daily_id` ustuni qo'shildi
    query = """
        SELECT id, daily_id, total_amount, status, created_at
        FROM orders
        WHERE user_id = $1
        ORDER BY created_at DESC;
    """
    async with pool.acquire() as conn:
        return await conn.fetch(query, user_id)


async def get_order(pool: asyncpg.Pool, order_id: int) -> asyncpg.Record | None:
    """
    ID bo‘yicha bitta buyurtma ma'lumotlarini to'liq qaytaradi.
    """
    query = "SELECT * FROM orders WHERE id = $1;"
    async with pool.acquire() as conn:
        return await conn.fetchrow(query, order_id)


async def get_order_receivers(pool: asyncpg.Pool, admin_ids: Collection[int] | None = None):
    """
    Yangi buyurtma haqida xabar olishi kerak bo'lganlarni (adminlarni) oladi.
    ``admin_ids`` berilsa, manba sifatida konfiguratsiya (ADMIN_IDS) ishlatiladi.
    """
    if admin_ids is not None:
        query = """
            SELECT id, selected_language_code, language_code
            FROM users
            WHERE id = ANY($1::bigint[])
            ORDER BY id;
        """
        return await pool.fetch(query, list(admin_ids))
    query = """
        SELECT id, selected_language_code, language_code
        FROM users
        WHERE role = 'admin'
        ORDER BY id;
    """
    async with pool.acquire() as conn:
        return await conn.fetch(query)


async def archive_product(pool: asyncpg.Pool, product_id: int) -> None:
    """
    Mahsulotni arxivlaydi (o'chirish o'rniga nofaol holatga o'tkazadi).
    """
    query = "UPDATE products SET is_available = FALSE WHERE id = $1;"
    async with pool.acquire() as conn:
        await conn.execute(query, product_id)


async def archive_category(pool: asyncpg.Pool, category_id: int) -> None:
    """
    Kategoriyani va uning barcha ichki kategoriyalarini arxivlaydi.
    """
    query = """
        WITH RECURSIVE subcats AS (
            SELECT id FROM categories WHERE id = $1
            UNION ALL
            SELECT c.id
            FROM categories c
            JOIN subcats s ON c.parent_id = s.id
        )
        UPDATE categories
        SET is_active = FALSE
        WHERE id IN (SELECT id FROM subcats);
    """
    async with pool.acquire() as conn:
        await conn.execute(query, category_id)


def get_paginated_sql_params(current_page: int, page_size: int = 10) -> tuple[int, int]:
    """
    Sahifalash uchun OFFSET va LIMIT qiymatlarini hisoblaydi.
    """
    if current_page < 0:
        current_page = 0
    offset = current_page * page_size
    return offset, page_size


async def count_toplevel_categories(pool: asyncpg.Pool) -> int:
    """
    Asosiy (eng yuqori darajadagi) kategoriyalar sonini sanaydi.
    """
    query = """
        SELECT COUNT(*) FROM categories
        WHERE parent_id IS NULL
          AND is_active = TRUE;
    """
    async with pool.acquire() as conn:
        return await conn.fetchval(query)


async def count_subcategories(pool: asyncpg.Pool, parent_id: int) -> int:
    """Ichki kategoriyalar sonini sanaydi."""
    sql = """
        SELECT COUNT(*) FROM categories
        WHERE parent_id = $1
          AND is_active = TRUE;
    """
    async with pool.acquire() as conn:
        return await conn.fetchval(sql, parent_id)


# --- ORDERS: Pagination helpers ---------------------------------------------
async def get_orders_by_status_paginated(
    pool: asyncpg.Pool,
    status: str,
    offset: int,
    limit: int,
) -> list[asyncpg.Record]:
    """Status bo'yicha buyurtmalarni sahifalab qaytaradi."""
    # <<< O'ZGARISH: SELECT ga `daily_id` qo'shildi
    sql = """
        SELECT id, daily_id, total_amount, created_at
        FROM orders
        WHERE status = $1
        ORDER BY created_at
        LIMIT $2 OFFSET $3;
    """
    async with pool.acquire() as conn:
        return await conn.fetch(sql, status, limit, offset)


async def count_orders_by_status(pool: asyncpg.Pool, status: str) -> int:
    """
    Ma'lum bir statusdagi buyurtmalar sonini sanaydi.
    """
    sql = """
        SELECT COUNT(*)
        FROM orders
        WHERE status = $1;
    """
    async with pool.acquire() as conn:
        return await conn.fetchval(sql, status)


async def get_orders_by_status_and_range(
    pool: asyncpg.Pool,
    status: str,
    date_from: datetime,
    date_to: datetime,
    limit: int,
    offset: int,
) -> list[asyncpg.Record]:
    """Belgilangan sana oralig'idagi va statusdagi buyurtmalarni qaytaradi."""
    # <<< O'ZGARISH: SELECT ga `daily_id` qo'shildi
    sql = """
        SELECT id, daily_id, total_amount, created_at
        FROM orders
        WHERE status      = $1
          AND created_at >= $2
          AND created_at <  $3
        ORDER BY created_at
        LIMIT $4 OFFSET $5;
    """
    async with pool.acquire() as conn:
        return await conn.fetch(sql, status, date_from, date_to, limit, offset)


async def count_orders_by_status_and_range(
    pool: asyncpg.Pool,
    status: str,
    date_from: datetime,
    date_to: datetime,
) -> int:
    """
    Belgilangan sana oralig'idagi va statusdagi buyurtmalar sonini sanaydi.
    """
    sql = """
        SELECT COUNT(*)
        FROM orders
        WHERE status      = $1
          AND created_at >= $2
          AND created_at <  $3;
    """
    async with pool.acquire() as conn:
        return await conn.fetchval(sql, status, date_from, date_to)


# --- Foydalanuvchining saqlangan manzillari bilan ishlash ---
# Bu funksiyalar yangi sxemaga mos va o'zgarishsiz qoladi.


async def add_saved_location(
    pool: asyncpg.Pool, user_id: int, name: str, latitude: float, longitude: float, address: str
) -> int:
    """Foydalanuvchi uchun yangi manzilni saqlaydi."""
    query = """
    INSERT INTO user_saved_locations
    (user_id, name, latitude, longitude, address_string)
    VALUES ($1, $2, $3, $4, $5)
    RETURNING id;
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, user_id, name, latitude, longitude, address)
        return row["id"]


async def get_saved_locations(pool: asyncpg.Pool, user_id: int) -> list[asyncpg.Record]:
    """Foydalanuvchining barcha saqlangan manzillarini qaytaradi."""
    query = """
    SELECT id, name, latitude, longitude, address_string
    FROM user_saved_locations
    WHERE user_id = $1
    ORDER BY id;
    """
    async with pool.acquire() as conn:
        return await conn.fetch(query, user_id)


async def delete_saved_location(pool: asyncpg.Pool, loc_id: int, user_id: int) -> None:
    """Foydalanuvchining saqlangan manzilini o'chiradi."""
    query = """
    DELETE FROM user_saved_locations
    WHERE id = $1 AND user_id = $2;
    """
    async with pool.acquire() as conn:
        await conn.execute(query, loc_id, user_id)


async def get_saved_location(pool: asyncpg.Pool, loc_id: int, user_id: int):
    """ID bo'yicha bitta saqlangan manzil ma'lumotini qaytaradi."""
    query = """
    SELECT latitude, longitude
    FROM user_saved_locations
    WHERE id = $1 AND user_id = $2;
    """
    async with pool.acquire() as conn:
        return await conn.fetchrow(query, loc_id, user_id)


# --- Tillarni Dinamik Boshqarish Funksiyalari ---
# Bu funksiyalar yangi funksional uchun kerak va o'zgarishsiz qoladi.


async def get_all_languages(pool: asyncpg.Pool) -> list[asyncpg.Record]:
    """Barcha tillarni ro'yxatini qaytaradi."""
    return await pool.fetch("SELECT * FROM languages ORDER BY code;")


async def get_enabled_languages(pool: asyncpg.Pool) -> list[asyncpg.Record]:
    """Faqat yoqilgan (is_enabled=TRUE) tillarni qaytaradi."""
    return await pool.fetch("SELECT * FROM languages WHERE is_enabled = TRUE ORDER BY code;")


async def toggle_language_status(pool: asyncpg.Pool, lang_code: str) -> None:
    """Berilgan tilning holatini (yoqiq/o'chiq) o'zgartiradi."""
    query = "UPDATE languages SET is_enabled = NOT is_enabled WHERE code = $1;"
    await pool.execute(query, lang_code)


async def update_user_location(pool: asyncpg.Pool, user_id: int, latitude: float, longitude: float) -> None:
    """Foydalanuvchining oxirgi joylashuvini va yangilangan vaqtini bazaga saqlaydi. (YANGI FUNKSIYA)"""
    query = """
        UPDATE users
        SET last_known_latitude = $2,
            last_known_longitude = $3,
            location_last_updated_at = $4
        WHERE id = $1;
    """
    # Vaqtni UTC (universal) formatida saqlaymiz
    await pool.execute(query, user_id, latitude, longitude, datetime.now(UTC))


# db_helpers.py fayliga qo'shing


async def reset_daily_order_counter(pool: asyncpg.Pool) -> None:
    """Kunlik raqamlash hisoblagichini nolga tushiradi (keyingi buyurtma #1 bo'ladi)."""
    await pool.execute("UPDATE order_counter SET last_value = 0, last_reset_at = CURRENT_TIMESTAMP WHERE id = 1;")


async def get_cafe_settings(pool: asyncpg.Pool) -> asyncpg.Record | None:
    """
    Cafe sozlamalarini bazadan oladi (bitta qatordan iborat).
    """
    query = "SELECT * FROM cafe_settings WHERE id = 1;"
    async with pool.acquire() as conn:
        return await conn.fetchrow(query)


async def update_cafe_location(pool: asyncpg.Pool, latitude: float, longitude: float) -> None:
    """
    Cafe joylashuv koordinatalarini yangilaydi.
    """
    query = """
        UPDATE cafe_settings
        SET latitude = $1,
            longitude = $2
        WHERE id = 1;
    """
    async with pool.acquire() as conn:
        await conn.execute(query, latitude, longitude)


async def update_cafe_radius(pool: asyncpg.Pool, radius_km: Decimal) -> None:
    """
    yetkazib berish radiusini (km) yangilaydi.
    """
    query = """
        UPDATE cafe_settings
        SET delivery_radius_km = $1
        WHERE id = 1;
    """
    async with pool.acquire() as conn:
        await conn.execute(query, radius_km)


async def add_courier(pool: asyncpg.Pool, user_id: int, full_name: str, phone_number: str | None = None) -> None:
    """
    Yangi kuriyer qo'shadi va foydalanuvchining rolini 'courier' ga o'rnatadi.
    """
    query = """
        INSERT INTO couriers (user_id, full_name, phone_number)
        VALUES ($1, $2, $3)
        ON CONFLICT (user_id) DO NOTHING;
    """
    async with pool.acquire() as conn:
        await conn.execute(query, user_id, full_name, phone_number)

    # Qo'shimcha: foydalanuvchi rolini 'courier' ga o'rnatamiz
    await set_user_role(pool, user_id, "courier")


async def get_all_couriers(pool: asyncpg.Pool) -> list[asyncpg.Record]:
    """
    Barcha faol kurerlarni ro'yxatini qaytaradi.
    """
    query = """
        SELECT * FROM couriers
        WHERE is_active = TRUE
        ORDER BY created_at;
    """
    return await pool.fetch(query)


async def get_courier(pool: asyncpg.Pool, user_id: int) -> asyncpg.Record | None:
    """
    user_id bo'yicha bitta kurer ma'lumotlarini qaytaradi.
    """
    query = "SELECT * FROM couriers WHERE user_id = $1;"
    async with pool.acquire() as conn:
        return await conn.fetchrow(query, user_id)


async def remove_courier(pool: asyncpg.Pool, user_id: int) -> None:
    """
    Kurerni o'chirmasdan, faolligini FALSE ga o'zgartiradi,
    so‘ngra foydalanuvchining rolini 'customer' ga tiklaydi.
    """
    # 1) Couriers jadvalidan faollikni o'chiramiz
    async with pool.acquire() as conn:
        await conn.execute("UPDATE couriers SET is_active = FALSE WHERE user_id = $1;", user_id)

    # 2) Foydalanuvchi rolini customer ga tiklaymiz
    await set_user_role(pool, user_id, "customer")


async def assign_courier_to_order(pool: asyncpg.Pool, order_id: int, courier_id: int) -> bool:
    """
    Buyurtmaga kurer tayinlaydi va statusni 'delivering' ga o'zgartiradi.
    Faqat 'processing' holatidagi buyurtmaga va faqat FAOL kuryerni tayinlash mumkin.
    Muvaffaqiyatli bo'lsa True qaytaradi.
    """
    query = """
        UPDATE orders o
        SET courier_id = $2,
            status     = 'delivering',
            updated_at = CURRENT_TIMESTAMP
        WHERE o.id = $1
          AND o.status = 'processing'
          AND EXISTS (SELECT 1 FROM couriers c WHERE c.user_id = $2 AND c.is_active)
        RETURNING o.id;
    """
    async with pool.acquire() as conn:
        return await conn.fetchval(query, order_id, courier_id) is not None


async def save_courier_message_id(pool: asyncpg.Pool, order_id: int, message_id: int) -> None:
    """Save the message_id of the courier notification in the orders table."""
    query = """
        UPDATE orders
        SET courier_message_id = $2
        WHERE id = $1;
    """
    async with pool.acquire() as conn:
        await conn.execute(query, order_id, message_id)


# db_helpers.py fayliga qo‘shing


async def get_courier_active_orders(pool: asyncpg.Pool, courier_id: int):
    """
    Kuryerga tayinlangan va 'delivering' statusdagi barcha buyurtmalarni qaytaradi.
    """
    query = """
        SELECT *
        FROM orders
        WHERE courier_id = $1
          AND status = 'delivering'
        ORDER BY created_at;
    """
    async with pool.acquire() as conn:
        return await conn.fetch(query, courier_id)


async def reactivate_courier(pool: asyncpg.Pool, user_id: int) -> None:
    """
    Inaktiv kuriyerni qayta faollashtiradi va foydalanuvchi rolini 'courier' ga tiklaydi.
    """
    async with pool.acquire() as conn:
        await conn.execute("UPDATE couriers SET is_active = TRUE WHERE user_id = $1;", user_id)
    # Foydalanuvchi rolini ham 'courier' ga tiklaymiz
    await set_user_role(pool, user_id, "courier")


async def get_couriers_with_status(pool: asyncpg.Pool) -> list[asyncpg.Record]:
    """
    Barcha faol kuriyerlarni ularning faol yetkazib berishlar soni bilan qaytaradi.
    """
    query = """
        SELECT
            c.user_id,
            c.full_name,
            c.phone_number,
            c.is_active,
            c.created_at,
            COUNT(o.id) AS active_orders_count
        FROM couriers c
        LEFT JOIN orders o
            ON c.user_id = o.courier_id
            AND o.status = 'delivering'
        WHERE
            c.is_active = TRUE
        GROUP BY
            c.user_id
        ORDER BY
            c.created_at;
    """
    async with pool.acquire() as conn:
        return await conn.fetch(query)


async def update_cancel_window(pool: asyncpg.Pool, minutes: int) -> None:
    """
    Cafe sozlamalaridagi order bekor qilish oynasini (daqiqa) yangilaydi.

    :param pool: asyncpg Pool obyekti
    :param minutes: bekor qilish oynasi (daqiqalarda)
    """
    query = """
        UPDATE cafe_settings
        SET cancel_window_minutes = $1
        WHERE id = 1;
    """
    async with pool.acquire() as conn:
        # $1 orqali parametr sifatida uzatilgan daqiqalarni yangilaymiz
        await conn.execute(query, minutes)


async def update_work_hours(pool: asyncpg.Pool, start_time: time, end_time: time) -> None:
    """
    Cafe sozlamalaridagi ish vaqtini yangilaydi.

    :param pool: asyncpg Pool obyekti
    :param start_time: ochilish vaqti (datetime.time)
    :param end_time:   yopilish vaqti (datetime.time)
    """
    query = """
        UPDATE cafe_settings
        SET work_hours_start = $1,    -- ochilish vaqtini yangilaydi
            work_hours_end   = $2     -- yopilish vaqtini yangilaydi
        WHERE id = 1;                 -- bitta qatordagi sozlamalar
    """
    # Ustunlarga start_time va end_time argumentlari bilan yangilash
    async with pool.acquire() as conn:
        await conn.execute(query, start_time, end_time)


async def update_order_buffer(pool: asyncpg.Pool, minutes: int) -> None:
    """
    Cafe sozlamalaridagi buyurtma qabul qilish uchun buffer vaqtini (daqiqa) yangilaydi.

    :param pool: asyncpg Pool obyekti
    :param minutes: buffer vaqti (daqiqalarda)
    """
    query = """
        UPDATE cafe_settings
        SET order_acceptance_buffer_minutes = $1  -- yangi ustunni parametr orqali yangilaymiz
        WHERE id = 1;                             -- faqat bitta sozlamalar qatorida
    """
    async with pool.acquire() as conn:
        # $1 orqali uzatilgan daqiqa qiymatini bazaga yozamiz
        await conn.execute(query, minutes)


async def toggle_product_availability(pool: asyncpg.Pool, product_id: int) -> None:
    """
    Mahsulotning `is_available` flagini teskari holatga o‘zgartiradi.
    Ya’ni, agar mavjud bo‘lsa — nofaol, aks holda — faol qiladi.
    """
    query = """
        UPDATE products
        SET is_available = NOT is_available
        WHERE id = $1;
    """
    async with pool.acquire() as conn:
        await conn.execute(query, product_id)


async def get_daily_report(
    pool: asyncpg.Pool,
    day_start: datetime,
    day_end: datetime,
) -> tuple[int, Decimal, str | None]:
    """
    Kunlik hisobot (``day_start`` <= created_at < ``day_end``, mahalliy kun chegaralari):
    - order_count: bugun statusi 'completed' bo‘lgan buyurtmalar soni
    - total_sum: bugungi bajarilgan buyurtmalarning umumiy summasi
    - best_seller_name: bugun eng ko‘p sotilgan mahsulot nomi (agar mavjud bo‘lsa)
    """
    async with pool.acquire() as conn:
        # 1) Bajarilgan buyurtmalar soni va ularning umumiy summasini olish
        #    COUNT(id) — buyurtmalar soni,
        #    COALESCE(SUM(total_amount), 0) — umumiy summa; agar hech buyurtma bo‘lmasa, 0 qaytaradi
        totals_query = """
            SELECT
                COUNT(id) AS order_count,
                COALESCE(SUM(total_amount), 0) AS total_sum
            FROM orders
            WHERE status = 'completed'
              AND created_at >= $1 AND created_at < $2;
        """
        totals_row = await conn.fetchrow(totals_query, day_start, day_end)
        order_count = totals_row["order_count"]
        total_sum = totals_row["total_sum"]

        # 2) Eng ko‘p sotilgan mahsulotni aniqlash
        #    order_items, orders va products jadvallarini birlashtirib,
        #    bugun bajarilgan buyurtmalardagi mahsulot miqdorlarini yig‘adi,
        #    so‘ng SUM(oi.quantity) bo‘yicha kamayish tartibida saralab,
        #    LIMIT 1 bilan faqat birinchi (eng yuqori) natijani oladi
        best_seller_query = """
            SELECT
                p.name AS product_name
            FROM order_items oi
            JOIN orders o   ON oi.order_id = o.id
            JOIN products p ON p.id        = oi.product_id
            WHERE o.status = 'completed'
              AND o.created_at >= $1 AND o.created_at < $2
            GROUP BY p.id, p.name
            ORDER BY SUM(oi.quantity) DESC, p.id
            LIMIT 1;
        """
        best_row = await conn.fetchrow(best_seller_query, day_start, day_end)
        best_seller_name = best_row["product_name"] if best_row else None

    return order_count, total_sum, best_seller_name


async def add_product_variation(
    pool: asyncpg.Pool,
    product_id: int,
    name_jsonb: dict,
    price: float,
    photo_file_id: str | None = None,  # Yangi: variatsiya rasmining file_idsi
) -> int:
    """
    Mahsulot uchun yangi variant qo'shadi,
    variatsiyaga xos rasmni saqlash uchun photo_file_id ustunini ham qo'llaydi,
    so'ngra ota mahsulotdagi has_variations flagini TRUE qiladi.
    """
    # JSON formatga o‘girib olamiz
    name_str = json.dumps(name_jsonb)

    async with pool.acquire() as conn, conn.transaction():
        # Qo‘shimcha ustun sifatida photo_file_id qo‘shildi
        insert_sql = """
            INSERT INTO product_variations
                (product_id, name, price, photo_file_id)
            VALUES ($1, $2, $3, $4)
            RETURNING id;
            """
        variation_id = await conn.fetchval(insert_sql, product_id, name_str, Decimal(price), photo_file_id)

        # Ota mahsulotga variatsiya borligini belgisi
        update_sql = "UPDATE products SET has_variations = TRUE WHERE id = $1;"
        await conn.execute(update_sql, product_id)

    return variation_id


async def get_product_variations(pool, product_id: int) -> list[asyncpg.Record]:
    """
    Berilgan product_id bo‘yicha BARCHA variantlarni qaytaradi.
    Holati (is_available) bo'yicha filtrlanmaydi.
    """
    select_sql = """
    SELECT id, product_id, name, price, is_available
      FROM product_variations
     WHERE product_id = $1
     ORDER BY id;
    """
    async with pool.acquire() as conn:
        records = await conn.fetch(select_sql, product_id)
    return records


async def get_variation_details_with_product_name(pool: asyncpg.Pool, variation_id: int) -> asyncpg.Record | None:
    """
    Bitta variant va uning ota mahsulotining kerakli ma'lumotlarini qaytaradi.
    ---
    O‘zgartirishlar:
    - pv.photo_file_id allaqachon mavjud edi (variant rasmi)
    - <<< QO‘SHILDI: p.category_id (back tugmasi uchun)
    """
    sql = """
    SELECT
      pv.id,
      pv.product_id,
      pv.name           AS variation_name,
      pv.price,
      pv.photo_file_id,    -- variant rasmi
      pv.is_available,
      p.name            AS product_name,
      p.category_id     AS category_id   -- <<< Qoʻshildi: ota mahsulot kategoriyasi
    FROM product_variations pv
    JOIN products p ON p.id = pv.product_id
    WHERE pv.id = $1;
    """
    async with pool.acquire() as conn:
        return await conn.fetchrow(sql, variation_id)


async def delete_variation(pool: asyncpg.Pool, variation_id: int) -> None:
    """
    Berilgan variatsiya ID bo'yicha product_variations jadvalidan yozuvni o'chiradi.
    """
    query = "DELETE FROM product_variations WHERE id = $1;"
    async with pool.acquire() as conn:
        await conn.execute(query, variation_id)


async def toggle_variation_availability(pool: asyncpg.Pool, variation_id: int) -> None:
    """
    Variatsiya `is_available` flagini teskari holatga o‘zgartiradi.
    """
    query = """
        UPDATE product_variations
        SET is_available = NOT is_available
        WHERE id = $1;
    """
    async with pool.acquire() as conn:
        await conn.execute(query, variation_id)


async def update_variation_price(pool: asyncpg.Pool, variation_id: int, new_price: float) -> None:
    """
    Variatsiya narxini yangilaydi.
    :param pool: asyncpg Pool obyekti
    :param variation_id: yangilanadigan variatsiya ID si
    :param new_price: yangi narx
    """
    query = "UPDATE product_variations SET price = $2 WHERE id = $1;"
    async with pool.acquire() as conn:
        await conn.execute(query, variation_id, new_price)


async def update_variation_name(
    pool: asyncpg.Pool,
    variation_id: int,
    new_name_jsonb: Mapping[str, str],
) -> None:
    """
    Variatsiya nomini yangilaydi.
    """
    # JSONB dictionary → JSON string
    name_str = json.dumps(new_name_jsonb)
    query = """
        UPDATE product_variations
        SET name = $2
        WHERE id   = $1;
    """
    async with pool.acquire() as conn:
        await conn.execute(query, variation_id, name_str)


async def update_variation_photo(pool: asyncpg.Pool, variation_id: int, new_photo_file_id: str | None) -> None:
    """
    Variatsiya rasmini yangilaydi yoki o'chiradi.
    :param pool: asyncpg Pool obyekti
    :param variation_id: yangilanadigan variatsiya ID si
    :param new_photo_file_id: yangi file_id (yoki None, agar rasmni olib tashlash kerak bo'lsa)
    """
    query = """
        UPDATE product_variations
        SET photo_file_id = $2
        WHERE id = $1;
    """
    async with pool.acquire() as conn:
        await conn.execute(query, variation_id, new_photo_file_id)
