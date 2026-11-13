"""Shared fixtures.

Database tests use a *real* PostgreSQL:

* ``TEST_DATABASE_URL`` set (CI) → that database is used (it is wiped between tests!);
* otherwise a throw-away ``postgres:16-alpine`` container is started with ``docker run``
  on a random localhost port and removed at the end of the session;
* neither available → database tests are skipped.

``DATABASE_URL`` is deliberately *not* used by tests so a production database can
never be truncated by accident.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import sys
import time
import uuid
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import asyncpg
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.config import Settings  # noqa: E402
from database_setup import apply_schema  # noqa: E402

PG_IMAGE = os.getenv("TEST_POSTGRES_IMAGE", "postgres:16-alpine")
TABLES = (
    "order_items, orders, product_variations, products, categories, couriers, "
    "user_saved_locations, users, order_counter, languages, cafe_settings"
)


def _docker(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["docker", *args], capture_output=True, text=True, check=check, timeout=120)


async def _can_connect(url: str) -> bool:
    try:
        conn = await asyncpg.connect(url, timeout=3)
    except (TimeoutError, OSError, asyncpg.PostgresError):
        return False
    try:
        return await conn.fetchval("SELECT 1") == 1
    finally:
        await conn.close()


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    url = os.getenv("TEST_DATABASE_URL")
    if url:
        yield url
        return

    if shutil.which("docker") is None or _docker("info", check=False).returncode != 0:
        pytest.skip("PostgreSQL tests need TEST_DATABASE_URL or a running Docker daemon")

    name = f"dastavka-test-{uuid.uuid4().hex[:8]}"
    _docker(
        "run", "-d", "--rm", "--name", name,
        "-e", "POSTGRES_USER=test", "-e", "POSTGRES_PASSWORD=test", "-e", "POSTGRES_DB=dastavka_test",
        "-p", "127.0.0.1::5432",
        PG_IMAGE,
    )  # fmt: skip
    try:
        host_port = _docker("port", name, "5432/tcp").stdout.strip().splitlines()[0]
        port = host_port.rsplit(":", 1)[1]
        url = f"postgresql://test:test@127.0.0.1:{port}/dastavka_test"
        deadline = time.monotonic() + 90
        while True:
            # pg_isready over TCP only succeeds after the init-time restart has finished.
            ready = _docker("exec", name, "pg_isready", "-h", "127.0.0.1", "-U", "test", check=False)
            if ready.returncode == 0 and asyncio.run(_can_connect(url)):
                break
            if time.monotonic() > deadline:
                raise RuntimeError(f"PostgreSQL container {name} did not become ready")
            time.sleep(0.5)
        yield url
    finally:
        _docker("rm", "-f", name, check=False)


@pytest.fixture
async def db_pool(database_url: str) -> AsyncIterator[asyncpg.Pool]:
    """Fresh, seeded schema for every test."""
    pool = await asyncpg.create_pool(database_url, min_size=1, max_size=10)
    async with pool.acquire() as conn:
        await apply_schema(conn)
        await conn.execute(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE")
        await apply_schema(conn)  # re-insert seed rows (counter, languages, cafe settings)
    try:
        yield pool
    finally:
        await pool.close()


ADMIN_ID = 1001
COURIER_ID = 2001
OTHER_COURIER_ID = 2002
CUSTOMER_ID = 3001
OTHER_CUSTOMER_ID = 3002
GROUP_ID = -100500


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        bot_token="123456:TEST-token_for_tests",
        admin_ids=str(ADMIN_ID),
        notification_group_id=None,
        timezone="Asia/Tashkent",
        database_url="postgresql://unused/unused",
    )
