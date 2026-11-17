"""Free-text inputs are bounded so one customer cannot break or bloat the database."""

import pytest

import db_helpers as db
from locales.lexicon import LEXICON
from tests.conftest import CUSTOMER_ID

pytestmark = pytest.mark.integration


async def _save_address(harness, name: str) -> None:
    await harness.click(CUSTOMER_ID, "add_new_address")
    await harness.send_location(CUSTOMER_ID, 41.312, 69.28)
    await harness.send(CUSTOMER_ID, name)


async def test_saved_address_name_length_is_checked(harness):
    await harness.send(CUSTOMER_ID, "/start")
    harness.clear()
    await _save_address(harness, "x" * 101)
    assert LEXICON["address_name_invalid"]["uz"] in harness.all_texts()
    assert await db.get_saved_locations(harness.pool, CUSTOMER_ID) == []
    await harness.send(CUSTOMER_ID, "Uy")  # still waiting for a name
    assert [r["name"] for r in await db.get_saved_locations(harness.pool, CUSTOMER_ID)] == ["Uy"]


async def test_saved_addresses_are_capped(harness):
    from handlers.user_handlers import MAX_SAVED_ADDRESSES

    await harness.send(CUSTOMER_ID, "/start")
    for i in range(MAX_SAVED_ADDRESSES + 2):
        await _save_address(harness, f"Manzil {i}")
    assert len(await db.get_saved_locations(harness.pool, CUSTOMER_ID)) == MAX_SAVED_ADDRESSES
    assert "10" in harness.all_texts()
