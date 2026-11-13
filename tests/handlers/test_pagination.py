"""Paging through long lists via the real Dispatcher: every « / » button must work."""

from decimal import Decimal

import pytest
from aiogram.methods import EditMessageText

import db_helpers as db
from locales.lexicon import LEXICON
from tests.conftest import ADMIN_ID, COURIER_ID, CUSTOMER_ID
from tests.factories import make_courier, make_order, make_user

pytestmark = pytest.mark.integration

DENIED = LEXICON["access_denied_alert"]["uz"]
N = 13  # page size is 10 → two pages (10 + 3)


def _last_edit(harness) -> EditMessageText:
    edits = harness.of_type(EditMessageText)
    assert edits, "nothing was rendered"
    return edits[-1]


def _buttons(edit: EditMessageText) -> dict[str, str]:
    """button text → callback_data"""
    return {b.text: b.callback_data for row in edit.reply_markup.inline_keyboard for b in row if b.callback_data}


async def _flip(harness, user_id: int, open_data: str) -> tuple[dict[str, str], dict[str, str]]:
    """Open a list, press », return (page 1 buttons, page 2 buttons) and then press « back."""
    await harness.click(user_id, open_data)
    page1 = _buttons(_last_edit(harness))
    assert "»" in page1 and "«" not in page1, f"no next-page button on {open_data!r}: {page1}"

    harness.clear()
    await harness.click(user_id, page1["»"])
    assert all(a.text != DENIED for a in harness.answers()), f"{page1['»']!r} was rejected by the fallback"
    page2 = _buttons(_last_edit(harness))
    assert "«" in page2 and "»" not in page2

    harness.clear()
    await harness.click(user_id, page2["«"])
    assert _buttons(_last_edit(harness)) == page1
    return page1, page2


def _names(page: dict[str, str], marker: str) -> set[str]:
    return {text for text in page if marker in text}


async def _categories(pool, n: int, parent_id: int | None = None, label: str = "Cat") -> list[int]:
    return [
        await db.add_category(pool, {"uz": f"{label} {i:02d}", "ru": f"{label} {i:02d}"}, parent_id)
        for i in range(1, n + 1)
    ]


@pytest.fixture
async def users(harness):
    await harness.send(ADMIN_ID, "/start")
    await make_user(harness.pool, CUSTOMER_ID)
    harness.clear()


async def test_customer_top_level_categories(harness, users):
    await _categories(harness.pool, N)
    page1, page2 = await _flip(harness, CUSTOMER_ID, "go_to_main_menu")
    assert len(_names(page1, "Cat ")) == 10
    assert _names(page2, "Cat ") == {f"📂 Cat {i:02d}" for i in (11, 12, 13)}
    assert page1["»"] == "customer_page:1"
    # cart / settings buttons are on every page
    assert {"view_cart", "customer_settings_menu"} <= set(page2.values())


async def test_customer_subcategories(harness, users):
    (parent,) = await _categories(harness.pool, 1, label="Parent")
    await _categories(harness.pool, N, parent_id=parent, label="Sub")
    page1, page2 = await _flip(harness, CUSTOMER_ID, f"customer_view_cat:{parent}:0")
    assert page1["»"] == f"customer_cat_page:{parent}:1:0"
    assert _names(page2, "Sub ") == {f"📂 Sub {i:02d}" for i in (11, 12, 13)}
    # items on page 2 open the right subcategory
    assert page2["📂 Sub 12"].startswith("customer_view_cat:")


async def test_customer_products_in_category(harness, users):
    (cat,) = await _categories(harness.pool, 1)
    for i in range(1, N + 1):
        await db.add_product(harness.pool, cat, {"uz": f"Taom {i:02d}"}, {}, "photo", Decimal("1000"))
    _page1, page2 = await _flip(harness, CUSTOMER_ID, f"customer_view_cat:{cat}:0")
    assert _names(page2, "Taom ") == {f"🍽️ Taom {i:02d}" for i in (11, 12, 13)}
    assert all(v.startswith("customer_view_prod:") for k, v in page2.items() if "Taom" in k)


async def test_admin_category_subcategory_and_product_lists(harness, users):
    pool = harness.pool
    await _categories(pool, N)
    page1, page2 = await _flip(harness, ADMIN_ID, "manage_categories")
    assert page1["»"] == "category_page:1"
    assert len(_names(page2, "Cat ")) == 3

    (parent,) = await _categories(pool, 1, label="Parent")
    await _categories(pool, N, parent_id=parent, label="Sub")
    page1, page2 = await _flip(harness, ADMIN_ID, f"category:{parent}:0")
    assert page1["»"] == f"subcategory_page:{parent}:1"
    assert len(_names(page2, "Sub ")) == 3

    (food,) = await _categories(pool, 1, label="Food")
    for i in range(1, N + 1):
        await db.add_product(pool, food, {"uz": f"Taom {i:02d}"}, {}, "photo", Decimal("1000"))
    page1, page2 = await _flip(harness, ADMIN_ID, f"category:{food}:0")
    assert page1["»"] == f"product_page:{food}:1"
    assert len(_names(page2, "Taom ")) == 3


async def test_admin_courier_list(harness, users):
    for i in range(N):
        await make_courier(harness.pool, 5000 + i, f"Kuryer {i:02d}")
    page1, page2 = await _flip(harness, ADMIN_ID, "manage_couriers_btn")
    assert page1["»"] == "courier_page:1"
    assert len(_names(page1, "Kuryer ")) == 10  # only the current page is rendered
    assert _names(page2, "Kuryer ") == {f"Kuryer {i:02d}" for i in (10, 11, 12)}
    assert "add_courier" in page2.values()


async def test_courier_active_deliveries(harness, users):
    pool = harness.pool
    await make_courier(pool, COURIER_ID)
    (cat,) = await _categories(pool, 1)
    prod = await db.add_product(pool, cat, {"uz": "Osh"}, {}, "photo", Decimal("1000"))
    for _ in range(N):
        order_id, _ = await make_order(pool, CUSTOMER_ID, prod, price="1000")
        await db.update_order_status(pool, order_id, "processing")
        assert await db.assign_courier_to_order(pool, order_id, COURIER_ID)

    page1, page2 = await _flip(harness, COURIER_ID, "my_active_deliveries")
    assert page1["»"] == "my_active_deliveries_page:1"
    tasks1 = [v for v in page1.values() if v.startswith("view_delivery_task:")]
    tasks2 = [v for v in page2.values() if v.startswith("view_delivery_task:")]
    assert (len(tasks1), len(tasks2)) == (10, 3)
    assert not set(tasks1) & set(tasks2)

    # a task opened from page 2 is viewable by its courier
    harness.clear()
    await harness.click(COURIER_ID, tasks2[0])
    assert "+998901234567" in harness.all_texts()


async def test_admin_orders_by_period(harness, users):
    pool = harness.pool
    (cat,) = await _categories(pool, 1)
    prod = await db.add_product(pool, cat, {"uz": "Osh"}, {}, "photo", Decimal("1000"))
    for _ in range(N):
        await make_order(pool, CUSTOMER_ID, prod, price="1000")
    page1, page2 = await _flip(harness, ADMIN_ID, "quick_date:pending:today")
    assert page1["»"].startswith("orders_period_page:pending:")
    orders2 = [v for v in page2.values() if v.startswith("view_order_details:")]
    assert len(orders2) == 3
