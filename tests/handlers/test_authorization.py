"""Crafted callback data must never reach a handler the caller is not allowed to use."""

from decimal import Decimal

import pytest
from aiogram.methods import SendMessage

import db_helpers as db
from locales.lexicon import LEXICON
from tests.conftest import ADMIN_ID, COURIER_ID, CUSTOMER_ID, GROUP_ID, OTHER_COURIER_ID, OTHER_CUSTOMER_ID
from tests.factories import make_courier, make_order, make_product, make_user

pytestmark = pytest.mark.integration

DENIED = LEXICON["access_denied_alert"]["uz"]
NOT_FOUND = LEXICON["order_not_found_alert"]["uz"]


@pytest.fixture
async def world(harness):
    """Admin, two couriers, two customers, one product and one order in every status."""
    pool = harness.pool
    await make_user(pool, ADMIN_ID, "Admin", role="admin")
    await make_courier(pool, COURIER_ID, "Kuryer Bir", "+998900000001")
    await make_courier(pool, OTHER_COURIER_ID, "Kuryer Ikki", "+998900000002")
    await make_user(pool, CUSTOMER_ID, "Ali")
    await make_user(pool, OTHER_CUSTOMER_ID, "Vali")
    cat_id, prod_id = await make_product(pool)

    orders = {}
    for status in ("pending", "processing", "delivering"):
        order_id, _ = await make_order(pool, CUSTOMER_ID, prod_id)
        orders[status] = order_id
    await db.update_order_status(pool, orders["processing"], "processing")
    await db.update_order_status(pool, orders["delivering"], "processing")
    assert await db.assign_courier_to_order(pool, orders["delivering"], COURIER_ID)
    harness.clear()
    return {"cat_id": cat_id, "prod_id": prod_id, "orders": orders}


async def _snapshot(pool):
    return {
        "orders": [tuple(r) for r in await pool.fetch("SELECT id, status, courier_id FROM orders ORDER BY id")],
        "products": [tuple(r) for r in await pool.fetch("SELECT id, is_available, price, name FROM products")],
        "categories": [tuple(r) for r in await pool.fetch("SELECT id, is_active FROM categories")],
        "couriers": [tuple(r) for r in await pool.fetch("SELECT user_id, is_active FROM couriers ORDER BY 1")],
        "languages": [tuple(r) for r in await pool.fetch("SELECT code, is_enabled FROM languages ORDER BY 1")],
        "counter": tuple(await pool.fetchrow("SELECT last_value, last_reset_at FROM order_counter")),
    }


ADMIN_CALLBACKS = [
    "admin_main_menu",
    "admin_view_orders",
    "accept_order:{pending}",
    "deliver_order:{processing}",
    "complete_order:{delivering}",
    "assign_courier:{processing}",
    "confirm_assign:{processing}:{courier}",
    "view_order_details:{delivering}",
    "view_orders_by_status:pending",
    "quick_date:pending:today",
    "manage_categories",
    "category:{cat}:0",
    "confirm_delete_category:{cat}",
    "final_delete_category:{cat}",
    "add_category",
    "add_product:{cat}",
    "product:{prod}:0",
    "edit_price:{prod}",
    "toggle_availability:{prod}",
    "confirm_delete_product:{prod}",
    "final_delete_product:{prod}",
    "manage_variations:{prod}",
    "add_variation:{prod}",
    "restaurant_settings",
    "manage_zone",
    "set_location_btn",
    "set_radius_btn",
    "set_work_hours",
    "set_order_buffer",
    "set_cancel_window",
    "manage_languages",
    "toggle_lang:en",
    "confirm_reset_daily_id",
    "final_reset_daily_id",
    "get_daily_report",
    "manage_team",
    "manage_couriers_btn",
    "add_courier",
    "courier:{courier}:0",
    "remove_courier:{courier}",
    "confirm_remove_courier:{courier}",
    "reactivate_courier_yes:{courier}",
    "admin_lang_select:ru",
]


@pytest.mark.parametrize("template", ADMIN_CALLBACKS)
@pytest.mark.parametrize("caller", [CUSTOMER_ID, COURIER_ID], ids=["customer", "courier"])
async def test_non_admin_cannot_use_admin_callbacks(harness, world, template, caller):
    data = template.format(cat=world["cat_id"], prod=world["prod_id"], courier=COURIER_ID, **world["orders"])
    before = await _snapshot(harness.pool)

    await harness.click(caller, data)

    answer = harness.last_answer()
    assert answer.text == DENIED and answer.show_alert
    # nothing changed in the DB, nobody else was messaged, no admin screen was rendered
    assert await _snapshot(harness.pool) == before
    assert harness.of_type(SendMessage) == []
    assert "Admin" not in harness.all_texts()
    # no FSM state was entered
    ctx = harness.dp.fsm.get_context(harness.bot, chat_id=caller, user_id=caller)
    assert await ctx.get_state() is None


async def test_admin_callback_from_group_member_is_rejected(harness, world):
    """Buttons posted in the notification group must not work for ordinary group members."""
    await harness.click(OTHER_CUSTOMER_ID, f"view_order_details:{world['orders']['pending']}", chat_id=GROUP_ID)
    assert harness.last_answer().text == DENIED
    assert "+998901234567" not in harness.all_texts()


async def test_stale_db_admin_role_grants_nothing(harness, world):
    """Only ADMIN_IDS counts; a leftover role='admin' row is demoted on the next update."""
    await db.set_user_role(harness.pool, OTHER_CUSTOMER_ID, "admin")
    await harness.click(OTHER_CUSTOMER_ID, f"accept_order:{world['orders']['pending']}")
    assert harness.last_answer().text == DENIED
    assert (await db.get_order(harness.pool, world["orders"]["pending"]))["status"] == "pending"
    assert (await db.get_user(harness.pool, OTHER_CUSTOMER_ID))["role"] == "customer"


async def test_non_admin_admin_fsm_text_is_ignored(harness, world):
    """Even with an admin FSM state forced into storage, admin message handlers don't run."""
    from handlers.admin.products import EditProductPriceFSM

    ctx = harness.dp.fsm.get_context(harness.bot, chat_id=CUSTOMER_ID, user_id=CUSTOMER_ID)
    await ctx.set_state(EditProductPriceFSM.waiting_price)
    await ctx.update_data(prod_id=world["prod_id"])
    await harness.send(CUSTOMER_ID, "1")
    product = await db.get_product(harness.pool, world["prod_id"])
    assert product["price"] == Decimal("25000.00")


async def test_customer_cannot_confirm_someone_elses_order(harness, world):
    order_id = world["orders"]["delivering"]
    for data in (f"cust_confirm_ok:{order_id}", f"cust_confirm_no:{order_id}"):
        harness.clear()
        await harness.click(OTHER_CUSTOMER_ID, data)
        assert harness.last_answer().text == NOT_FOUND
        assert (await db.get_order(harness.pool, order_id))["status"] == "delivering"
        assert harness.of_type(SendMessage) == []  # admins were not told it was completed


async def test_owner_cannot_confirm_order_that_is_not_being_delivered(harness, world):
    order_id = world["orders"]["pending"]
    await harness.click(CUSTOMER_ID, f"cust_confirm_ok:{order_id}")
    assert harness.last_answer().text == NOT_FOUND
    assert (await db.get_order(harness.pool, order_id))["status"] == "pending"


async def test_customer_cannot_open_cancel_dialog_for_foreign_order(harness, world):
    order_id = world["orders"]["pending"]
    await harness.click(OTHER_CUSTOMER_ID, f"confirm_cancel_order:{order_id}")
    assert harness.last_answer().text == NOT_FOUND
    await harness.click(OTHER_CUSTOMER_ID, f"final_cancel_order:{order_id}")
    assert (await db.get_order(harness.pool, order_id))["status"] == "pending"


async def test_customer_cannot_view_foreign_order_details(harness, world):
    await harness.click(OTHER_CUSTOMER_ID, f"customer_view_order_details:{world['orders']['pending']}")
    assert "+998901234567" not in harness.all_texts()


@pytest.mark.parametrize("data", ["view_delivery_task:{id}:0", "deliver_confirm:{id}"])
async def test_non_assigned_courier_cannot_see_or_confirm_delivery(harness, world, data):
    order_id = world["orders"]["delivering"]
    await harness.click(OTHER_COURIER_ID, data.format(id=order_id))

    assert harness.last_answer().text == NOT_FOUND
    texts = harness.all_texts()
    assert "Ali" not in texts and "+998901234567" not in texts  # no customer data leaked
    assert harness.sent_to(CUSTOMER_ID) == []  # customer was not asked to confirm


@pytest.mark.parametrize("data", ["view_delivery_task:{id}:0", "deliver_confirm:{id}", "my_active_deliveries"])
async def test_customer_cannot_use_courier_callbacks(harness, world, data):
    await harness.click(OTHER_CUSTOMER_ID, data.format(id=world["orders"]["delivering"]))
    assert harness.last_answer().text == DENIED
    assert "+998901234567" not in harness.all_texts()


async def test_deactivated_courier_loses_access(harness, world):
    await db.remove_courier(harness.pool, COURIER_ID)
    await harness.click(COURIER_ID, f"view_delivery_task:{world['orders']['delivering']}:0")
    assert harness.last_answer().text == DENIED


async def test_assigned_courier_can_view_task(harness, world):
    await harness.click(COURIER_ID, f"view_delivery_task:{world['orders']['delivering']}:0")
    assert "+998901234567" in harness.all_texts()


async def test_courier_cannot_view_order_not_in_delivery(harness, world):
    pool = harness.pool
    order_id = world["orders"]["delivering"]
    await db.transition_order_status(pool, order_id, from_statuses=("delivering",), to_status="completed")
    await harness.click(COURIER_ID, f"view_delivery_task:{order_id}:0")
    assert harness.last_answer().text == NOT_FOUND


@pytest.mark.parametrize("data", ["accept_order:abc", "confirm_assign:1", "view_delivery_task:x", "cust_confirm_ok:"])
async def test_malformed_callback_data_is_handled(harness, world, data):
    for caller in (ADMIN_ID, COURIER_ID, CUSTOMER_ID):
        harness.clear()
        await harness.click(caller, data)
        assert harness.answers(), f"{data!r} from {caller} left the callback unanswered"


async def test_set_group_explains_to_non_admin(harness, world):
    await harness.send(CUSTOMER_ID, "/set_group", chat_id=GROUP_ID)
    assert harness.sent_to(GROUP_ID)[-1].text == LEXICON["must_be_admin_error"]["uz"]
    harness.clear()
    await harness.send(ADMIN_ID, "/set_group", chat_id=GROUP_ID)
    assert f"NOTIFICATION_GROUP_ID={GROUP_ID}" in harness.sent_to(GROUP_ID)[-1].text
