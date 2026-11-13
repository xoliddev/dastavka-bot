"""Small helpers that put rows into the test database."""

from __future__ import annotations

from decimal import Decimal

import asyncpg

import db_helpers as db


async def make_user(pool: asyncpg.Pool, user_id: int, name: str = "User", role: str = "customer") -> None:
    await db.add_user(pool, user_id, name, None, "uz", role=role)


async def make_courier(pool: asyncpg.Pool, user_id: int, name: str = "Kuryer", phone: str = "+998900000000") -> None:
    if await db.get_user(pool, user_id) is None:
        await make_user(pool, user_id, name)
    await db.add_courier(pool, user_id, name, phone)


async def make_product(
    pool: asyncpg.Pool, price: str = "25000.00", name: str = "Osh", photo: str = "photo-file-id"
) -> tuple[int, int]:
    cat_id = await db.add_category(pool, {"uz": "Taomlar", "ru": "Блюда", "en": "Dishes"})
    prod_id = await db.add_product(pool, cat_id, {"uz": name, "ru": name, "en": name}, {}, photo, Decimal(price))
    return cat_id, prod_id


async def make_order(
    pool: asyncpg.Pool,
    user_id: int,
    product_id: int,
    *,
    quantity: int = 1,
    price: str = "25000.00",
    variation_id: int | None = None,
) -> tuple[int, int]:
    if await db.get_user(pool, user_id) is None:
        await make_user(pool, user_id)
    items = [
        {"product_id": product_id, "variation_id": variation_id, "quantity": quantity, "price_per_item": Decimal(price)}
    ]
    return await db.create_order(
        pool,
        user_id=user_id,
        final_order_details=items,
        total_amount=Decimal(price) * quantity,
        phone="+998901234567",
        latitude=41.3,
        longitude=69.24,
        customer_name="Ali",
    )
