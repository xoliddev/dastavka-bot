"""Schema setup is idempotent and migrates databases created by the pre-2.0 script."""

import asyncpg
import pytest

from database_setup import apply_schema

pytestmark = pytest.mark.integration

# The relevant part of the original (pre-2.0) schema.
LEGACY_SCHEMA = """
CREATE TABLE users (id BIGINT PRIMARY KEY, first_name VARCHAR(255) NOT NULL, username VARCHAR(255),
    language_code VARCHAR(10), selected_language_code VARCHAR(10), role VARCHAR(50) NOT NULL DEFAULT 'customer',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, last_known_latitude DOUBLE PRECISION,
    last_known_longitude DOUBLE PRECISION, location_last_updated_at TIMESTAMPTZ);
CREATE TABLE order_counter (id INT PRIMARY KEY DEFAULT 1, last_reset_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP);
INSERT INTO order_counter (id, last_reset_at) VALUES (1, now() - interval '1 hour');
CREATE TABLE categories (id SERIAL PRIMARY KEY, parent_id INTEGER REFERENCES categories(id) ON DELETE CASCADE,
    name JSONB NOT NULL, is_active BOOLEAN DEFAULT TRUE, created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE products (id SERIAL PRIMARY KEY, category_id INTEGER NOT NULL REFERENCES categories(id),
    name JSONB NOT NULL, description JSONB, price DECIMAL(12, 2) NOT NULL, photo_file_id VARCHAR(255),
    is_available BOOLEAN DEFAULT TRUE, created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE couriers (user_id BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    full_name VARCHAR(255) NOT NULL, phone_number VARCHAR(32), is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE orders (id SERIAL PRIMARY KEY, daily_id INTEGER, user_id BIGINT NOT NULL REFERENCES users(id),
    total_amount DECIMAL(12,2) NOT NULL DEFAULT 0.00, status VARCHAR(32) NOT NULL DEFAULT 'pending',
    customer_name VARCHAR(255), customer_phone VARCHAR(32), latitude DOUBLE PRECISION, longitude DOUBLE PRECISION,
    courier_id BIGINT REFERENCES couriers(user_id) ON DELETE SET NULL, courier_message_id BIGINT,
    cancel_window_minutes INTEGER, created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE order_items (id SERIAL PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE RESTRICT, quantity INTEGER NOT NULL CHECK (quantity > 0),
    price_per_item DECIMAL(12,2) NOT NULL, CONSTRAINT unique_order_product UNIQUE(order_id, product_id));
INSERT INTO users (id, first_name) VALUES (1, 'Old');
INSERT INTO orders (daily_id, user_id, created_at) VALUES (1, 1, now() - interval '2 hours'),
    (6, 1, now() - interval '30 minutes'), (7, 1, now() - interval '10 minutes');
"""


@pytest.fixture
async def scratch_db(database_url):
    """A brand-new empty database (dropped afterwards)."""
    admin = await asyncpg.connect(database_url)
    name = "schema_scratch"
    await admin.execute(f"DROP DATABASE IF EXISTS {name}")
    await admin.execute(f"CREATE DATABASE {name}")
    url = database_url.rsplit("/", 1)[0] + f"/{name}"
    conn = await asyncpg.connect(url)
    try:
        yield conn
    finally:
        await conn.close()
        await admin.execute(f"DROP DATABASE IF EXISTS {name}")
        await admin.close()


async def test_apply_schema_is_idempotent(scratch_db):
    await apply_schema(scratch_db)
    await apply_schema(scratch_db)
    await apply_schema(scratch_db)
    assert await scratch_db.fetchval("SELECT count(*) FROM languages") == 3
    assert await scratch_db.fetchval("SELECT count(*) FROM cafe_settings") == 1
    assert await scratch_db.fetchval("SELECT last_value FROM order_counter WHERE id = 1") == 0


async def test_legacy_database_is_migrated(scratch_db):
    await scratch_db.execute(LEGACY_SCHEMA)
    await apply_schema(scratch_db)

    # counter continues after the highest daily_id since the last reset (6, 7 → 7), not from 1
    assert await scratch_db.fetchval("SELECT last_value FROM order_counter WHERE id = 1") == 7
    cols = {r["column_name"] for r in await scratch_db.fetch(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'order_items'"
    )}  # fmt: skip
    assert "variation_id" in cols
    constraints = {r["conname"] for r in await scratch_db.fetch("SELECT conname FROM pg_constraint")}
    assert "unique_order_product" not in constraints

    # re-applying does not touch the counter again
    await scratch_db.execute("UPDATE order_counter SET last_value = 9")
    await apply_schema(scratch_db)
    assert await scratch_db.fetchval("SELECT last_value FROM order_counter WHERE id = 1") == 9


async def test_database_setup_script_main(database_url, monkeypatch):
    """`python database_setup.py` still works and reads the same env vars as the bot."""
    import database_setup

    monkeypatch.setenv("DATABASE_URL", database_url)
    assert await database_setup.main() == 0
    monkeypatch.setenv("DATABASE_URL", "postgresql://nobody:wrong@127.0.0.1:1/none")
    assert await database_setup.main() == 1
