#!/usr/bin/env python3
"""Idempotent database schema setup / migration.

The bot runs :func:`apply_schema` automatically on startup, so running this
script by hand is optional::

    python database_setup.py

Every statement is safe to re-run (``IF NOT EXISTS`` / ``ON CONFLICT``), and the
whole script runs in one transaction guarded by an advisory lock so several bot
replicas can start at the same time.
"""

from __future__ import annotations

import asyncio
import logging
import sys

import asyncpg

# Arbitrary constant used as the advisory-lock key for schema migrations.
SCHEMA_LOCK_ID = 0x64617374  # "dast"

SQL_SCHEMA = """
/* === 1. Asosiy jadvallar (boshqa jadvallarga bog'liq emas) === */

CREATE TABLE IF NOT EXISTS users (
    id BIGINT PRIMARY KEY,
    first_name VARCHAR(255) NOT NULL,
    username VARCHAR(255),
    language_code VARCHAR(10),
    selected_language_code VARCHAR(10),
    role VARCHAR(50) NOT NULL DEFAULT 'customer',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    last_known_latitude DOUBLE PRECISION,
    last_known_longitude DOUBLE PRECISION,
    location_last_updated_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS order_counter (
    id INT PRIMARY KEY DEFAULT 1,
    last_reset_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO order_counter (id, last_reset_at) VALUES (1, CURRENT_TIMESTAMP) ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS languages (
    code VARCHAR(10) PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    is_enabled BOOLEAN DEFAULT FALSE
);
INSERT INTO languages (code, name, is_enabled) VALUES
    ('uz', '🇺🇿 O‘zbekcha', TRUE),
    ('ru', '🇷🇺 Русский', TRUE),
    ('en', '🇺🇸 English', FALSE)
ON CONFLICT (code) DO NOTHING;

CREATE TABLE IF NOT EXISTS cafe_settings (
    id INTEGER PRIMARY KEY,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    delivery_radius_km DECIMAL(5,2),
    cancel_window_minutes INTEGER DEFAULT 5,
    order_acceptance_buffer_minutes INTEGER DEFAULT 15,  -- buyurtma qabul qilish bufer vaqti (daqiqa)
    work_hours_start TIME,                               -- ochilish vaqti (mahalliy, TIMEZONE bo'yicha)
    work_hours_end TIME                                  -- yopilish vaqti (yarim tundan o'tishi mumkin)
);
INSERT INTO cafe_settings (
    id, latitude, longitude, delivery_radius_km, cancel_window_minutes,
    order_acceptance_buffer_minutes, work_hours_start, work_hours_end
) VALUES (1, NULL, NULL, NULL, 5, 15, NULL, NULL)
ON CONFLICT (id) DO NOTHING;

/* === 2. Boshqa jadvallarga bog'liq jadvallar === */

CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    parent_id INTEGER REFERENCES categories(id) ON DELETE CASCADE,
    name JSONB NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    name JSONB NOT NULL,
    description JSONB,
    price DECIMAL(12, 2) NOT NULL,
    photo_file_id VARCHAR(255),
    is_available BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS couriers (
    user_id BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    full_name VARCHAR(255) NOT NULL,
    phone_number VARCHAR(32),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_saved_locations (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    address_string TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

/* === 3. Ko'p jadvallarga bog'liq jadvallar === */

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    daily_id INTEGER,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    total_amount DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    customer_name VARCHAR(255),
    customer_phone VARCHAR(32),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    courier_id BIGINT REFERENCES couriers(user_id) ON DELETE SET NULL,
    courier_message_id BIGINT,
    cancel_window_minutes INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    price_per_item DECIMAL(12,2) NOT NULL
);

-- Mahsulot variantlari
CREATE TABLE IF NOT EXISTS product_variations (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    name JSONB NOT NULL,
    price DECIMAL(12, 2) NOT NULL,
    photo_file_id VARCHAR(255),
    is_available BOOLEAN DEFAULT TRUE
);

ALTER TABLE products ADD COLUMN IF NOT EXISTS has_variations BOOLEAN DEFAULT FALSE;

ALTER TABLE order_items
  ADD COLUMN IF NOT EXISTS variation_id INTEGER REFERENCES product_variations(id) ON DELETE SET NULL;

/* === 4. Migratsiyalar (2.0) === */

-- Bir buyurtmada bitta mahsulotning bir nechta varianti bo'lishi mumkin, shuning uchun
-- eski UNIQUE(order_id, product_id) cheklovi o'rniga variantni ham hisobga olamiz.
ALTER TABLE order_items DROP CONSTRAINT IF EXISTS unique_order_product;
CREATE UNIQUE INDEX IF NOT EXISTS uq_order_items_order_product_variation
    ON order_items (order_id, product_id, COALESCE(variation_id, 0));

-- daily_id endi atomik hisoblagichdan olinadi (UPDATE ... RETURNING), MAX()+1 emas.
ALTER TABLE order_counter ADD COLUMN IF NOT EXISTS last_value INTEGER NOT NULL DEFAULT 0;
UPDATE order_counter oc
   SET last_value = GREATEST(
       oc.last_value,
       COALESCE((SELECT MAX(o.daily_id) FROM orders o WHERE o.created_at >= oc.last_reset_at), 0)
   )
 WHERE oc.id = 1;

/* === 5. Indekslar === */
CREATE INDEX IF NOT EXISTS idx_categories_parent ON categories(parent_id);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status_created ON orders(status, created_at);
CREATE INDEX IF NOT EXISTS idx_orders_courier ON orders(courier_id) WHERE courier_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_user_locations_user ON user_saved_locations(user_id);
"""


async def apply_schema(conn: asyncpg.Connection) -> None:
    """Create or migrate the schema. Safe to call on every startup."""
    async with conn.transaction():
        await conn.execute("SELECT pg_advisory_xact_lock($1)", SCHEMA_LOCK_ID)
        await conn.execute(SQL_SCHEMA)


async def main() -> int:
    from core.config import Settings

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    settings = Settings()
    try:
        conn = await asyncpg.connect(dsn=settings.postgres_dsn)
    except (OSError, asyncpg.PostgresError) as exc:
        logging.error("❌ Bazaga ulanib bo‘lmadi: %s", exc)
        return 1
    try:
        await apply_schema(conn)
        logging.info("✅ Ma'lumotlar bazasi sxemasi muvaffaqiyatli yangilandi!")
        return 0
    except asyncpg.PostgresError as exc:
        logging.error("❌ Jadvallarni yaratishda xatolik: %s", exc)
        return 1
    finally:
        await conn.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
