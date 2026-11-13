"""End-to-end happy path through the real Dispatcher, plus checkout rules."""

from datetime import datetime, time, timedelta
from decimal import Decimal

import pytest

import db_helpers as db
from handlers.customer_handlers import OrderFSM
from locales.lexicon import LEXICON
from tests.conftest import ADMIN_ID, COURIER_ID, CUSTOMER_ID, OTHER_COURIER_ID
from tests.factories import make_courier, make_product, make_user

pytestmark = pytest.mark.integration

CAFE = (41.3111, 69.2797)


@pytest.fixture
async def shop(harness):
    pool = harness.pool
    await harness.send(ADMIN_ID, "/start")  # admin registers via /start like in production
    await make_courier(pool, COURIER_ID, "Kuryer Bir", "+998900000001")
    await make_courier(pool, OTHER_COURIER_ID, "Kuryer Ikki", "+998900000002")
    _, prod_id = await make_product(pool, price="30000.00", name="Lag'mon")
    harness.clear()
    return prod_id


async def _checkout(harness, prod_id: int, qty: int = 2, location=(41.312, 69.28)):
    """Customer: open product → set quantity → add to cart → place order → name → phone → location."""
    await harness.click(CUSTOMER_ID, f"customer_view_prod:{prod_id}:0")
    for _ in range(qty - 1):
        await harness.click(CUSTOMER_ID, f"incr_qty:product:{prod_id}")
    await harness.click(CUSTOMER_ID, f"add_N_to_cart:product:{prod_id}")
    await harness.click(CUSTOMER_ID, "view_cart")
    await harness.click(CUSTOMER_ID, "place_order")
    await harness.send(CUSTOMER_ID, "Ali <b>Valiyev</b>")
    await harness.send(CUSTOMER_ID, "+998901234567")
    await harness.send_location(CUSTOMER_ID, *location)


async def test_full_order_lifecycle(harness, shop):
    pool, prod_id = harness.pool, shop

    # ── customer places the order ───────────────────────────
    await harness.send(CUSTOMER_ID, "/start")
    await _checkout(harness, prod_id, qty=2)

    orders = await db.get_user_orders(pool, CUSTOMER_ID)
    assert len(orders) == 1
    order_id = orders[0]["id"]
    order = await db.get_order(pool, order_id)
    assert (order["status"], order["daily_id"], order["total_amount"]) == ("pending", 1, Decimal("60000.00"))
    assert order["customer_name"] == "Ali <b>Valiyev</b>"
    assert harness.sent_to(CUSTOMER_ID)[-1].text == LEXICON["order_placed_success"]["uz"]

    # admin was notified with a details button; user-supplied HTML was escaped
    admin_msg = harness.sent_to(ADMIN_ID)[-1]
    assert f"view_order_details:{order_id}" in harness.buttons(admin_msg)
    assert "&lt;b&gt;Valiyev&lt;/b&gt;" in admin_msg.text

    # ── admin accepts and assigns a courier ─────────────────
    harness.clear()
    await harness.click(ADMIN_ID, f"view_order_details:{order_id}")
    await harness.click(ADMIN_ID, f"accept_order:{order_id}")
    assert harness.last_answer().text == LEXICON["order_accepted_alert"]["uz"]
    assert (await db.get_order(pool, order_id))["status"] == "processing"

    # double click on the stale "accept" button is a no-op with a clear message
    await harness.click(ADMIN_ID, f"accept_order:{order_id}")
    assert harness.last_answer().text == LEXICON["order_status_conflict_alert"]["uz"]

    await harness.click(ADMIN_ID, f"assign_courier:{order_id}")
    await harness.click(ADMIN_ID, f"confirm_assign:{order_id}:{COURIER_ID}")
    order = await db.get_order(pool, order_id)
    assert (order["status"], order["courier_id"]) == ("delivering", COURIER_ID)
    courier_msg = harness.sent_to(COURIER_ID)[-1]
    assert f"deliver_confirm:{order_id}" in harness.buttons(courier_msg)
    assert order["courier_message_id"] is not None
    assert harness.sent_to(CUSTOMER_ID), "customer is told which courier is coming"

    # ── courier ─────────────────────────────────────────────
    harness.clear()
    await harness.send(COURIER_ID, "/start")
    await harness.click(COURIER_ID, "my_active_deliveries")
    await harness.click(COURIER_ID, f"view_delivery_task:{order_id}:0")
    assert "+998901234567" in harness.all_texts()
    await harness.click(COURIER_ID, f"deliver_confirm:{order_id}")
    ask = harness.sent_to(CUSTOMER_ID)[-1]
    assert harness.buttons(ask) == [f"cust_confirm_ok:{order_id}", f"cust_confirm_no:{order_id}"]

    # ── customer confirms ───────────────────────────────────
    harness.clear()
    await harness.click(CUSTOMER_ID, f"cust_confirm_ok:{order_id}")
    assert (await db.get_order(pool, order_id))["status"] == "completed"
    assert harness.sent_to(ADMIN_ID), "admin is told the order is completed"
    # a second click (e.g. from another device) changes nothing
    await harness.click(CUSTOMER_ID, f"cust_confirm_no:{order_id}")
    assert (await db.get_order(pool, order_id))["status"] == "completed"

    # ── daily report sees it ────────────────────────────────
    harness.clear()
    await harness.click(ADMIN_ID, "get_daily_report")
    assert "60000" in harness.last_answer().text


async def test_customer_can_dispute_delivery(harness, shop):
    await _checkout(harness, shop, qty=1)
    order_id = (await db.get_user_orders(harness.pool, CUSTOMER_ID))[0]["id"]
    await harness.click(ADMIN_ID, f"accept_order:{order_id}")
    await harness.click(ADMIN_ID, f"confirm_assign:{order_id}:{COURIER_ID}")
    await harness.click(COURIER_ID, f"deliver_confirm:{order_id}")
    await harness.click(CUSTOMER_ID, f"cust_confirm_no:{order_id}")
    assert (await db.get_order(harness.pool, order_id))["status"] == "disputed"
    # admin can still close a disputed order
    await harness.click(ADMIN_ID, f"complete_order:{order_id}")
    assert (await db.get_order(harness.pool, order_id))["status"] == "completed"


async def test_checkout_outside_delivery_zone_is_refused(harness, shop):
    await db.update_cafe_location(harness.pool, *CAFE)
    await db.update_cafe_radius(harness.pool, 3)
    far_away = (41.55, 69.28)  # ~26 km north

    await _checkout(harness, shop, location=far_away)

    assert await db.get_user_orders(harness.pool, CUSTOMER_ID) == []
    assert harness.sent_to(CUSTOMER_ID)[-1].text == LEXICON["order_location_out_of_zone"]["uz"]
    ctx = harness.dp.fsm.get_context(harness.bot, chat_id=CUSTOMER_ID, user_id=CUSTOMER_ID)
    assert await ctx.get_state() == OrderFSM.waiting_for_location.state  # can retry

    # retrying from inside the zone works
    await harness.send_location(CUSTOMER_ID, CAFE[0] + 0.005, CAFE[1])
    assert len(await db.get_user_orders(harness.pool, CUSTOMER_ID)) == 1


async def test_order_refused_outside_working_hours(harness, shop, settings):
    now = datetime.now(settings.tz)
    # a shift that ended an hour ago and opens again in two hours
    await db.update_work_hours(
        harness.pool, (now + timedelta(hours=2)).time().replace(second=0, microsecond=0),
        (now - timedelta(hours=1)).time().replace(second=0, microsecond=0),
    )  # fmt: skip
    await harness.click(CUSTOMER_ID, f"customer_view_prod:{shop}:0")
    await harness.click(CUSTOMER_ID, f"add_N_to_cart:product:{shop}")
    harness.clear()
    await harness.click(CUSTOMER_ID, "place_order")
    assert harness.last_answer().show_alert
    assert "dan" in harness.last_answer().text  # cafe_is_closed_tpl
    ctx = harness.dp.fsm.get_context(harness.bot, chat_id=CUSTOMER_ID, user_id=CUSTOMER_ID)
    assert await ctx.get_state() is None


async def test_overnight_shift_accepts_orders_after_midnight(harness, shop, settings, monkeypatch):
    await db.update_work_hours(harness.pool, time(18), time(3))
    fake_now = datetime(2026, 11, 14, 1, 15, tzinfo=settings.tz)

    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fake_now if tz is None else fake_now.astimezone(tz)

    monkeypatch.setattr("handlers.customer_handlers.datetime", FrozenDatetime)
    await harness.click(CUSTOMER_ID, f"customer_view_prod:{shop}:0")
    await harness.click(CUSTOMER_ID, f"add_N_to_cart:product:{shop}")
    await harness.click(CUSTOMER_ID, "place_order")
    ctx = harness.dp.fsm.get_context(harness.bot, chat_id=CUSTOMER_ID, user_id=CUSTOMER_ID)
    assert await ctx.get_state() == OrderFSM.waiting_for_name.state


async def test_customer_cancel_within_window_only(harness, shop):
    await _checkout(harness, shop, qty=1)
    order_id = (await db.get_user_orders(harness.pool, CUSTOMER_ID))[0]["id"]

    await db.update_cancel_window(harness.pool, 5)
    await harness.pool.execute("UPDATE orders SET created_at = now() - interval '6 minutes' WHERE id = $1", order_id)
    await harness.click(CUSTOMER_ID, f"final_cancel_order:{order_id}")
    assert harness.last_answer().text == LEXICON["unable_to_cancel_alert"]["uz"]
    assert (await db.get_order(harness.pool, order_id))["status"] == "pending"

    await harness.pool.execute("UPDATE orders SET created_at = now() WHERE id = $1", order_id)
    await harness.click(CUSTOMER_ID, f"final_cancel_order:{order_id}")
    assert (await db.get_order(harness.pool, order_id))["status"] == "canceled"


async def test_deactivated_courier_can_be_re_added(harness, shop):
    """Regression: the duplicated fsm_courier_id made the reactivation branch unreachable."""
    pool = harness.pool
    await db.remove_courier(pool, COURIER_ID)

    await harness.click(ADMIN_ID, "add_courier")
    harness.clear()
    await harness.send(ADMIN_ID, str(COURIER_ID))
    prompt = harness.sent_to(ADMIN_ID)[-1]
    assert f"reactivate_courier_yes:{COURIER_ID}" in harness.buttons(prompt)

    await harness.click(ADMIN_ID, f"reactivate_courier_yes:{COURIER_ID}")
    assert (await db.get_courier(pool, COURIER_ID))["is_active"] is True
    assert (await db.get_user(pool, COURIER_ID))["role"] == "courier"


async def test_active_courier_cannot_be_added_twice(harness, shop):
    await harness.click(ADMIN_ID, "add_courier")
    harness.clear()
    await harness.send(ADMIN_ID, str(COURIER_ID))
    assert harness.sent_to(ADMIN_ID)[-1].text == LEXICON["user_is_already_active_courier"]["uz"]


async def test_add_new_courier(harness, shop):
    await make_user(harness.pool, 4242, "Yangi")
    await harness.click(ADMIN_ID, "add_courier")
    await harness.send(ADMIN_ID, "4242")
    await harness.send(ADMIN_ID, "Yangi Kuryer")
    await harness.send(ADMIN_ID, "/skip")
    courier = await db.get_courier(harness.pool, 4242)
    assert (courier["full_name"], courier["phone_number"], courier["is_active"]) == ("Yangi Kuryer", None, True)


async def test_restaurant_settings_menu_renders_once(harness, shop):
    """Regression: cb_restaurant_settings used to be defined twice."""
    await harness.click(ADMIN_ID, "restaurant_settings")
    edits = [r for r in harness.session.requests if type(r).__name__ == "EditMessageText"]
    assert len(edits) == 1
    assert edits[0].text == LEXICON["settings_title"]["uz"]


async def test_admin_quick_date_filter_uses_cafe_timezone(harness, shop):
    await _checkout(harness, shop, qty=1)
    harness.clear()
    await harness.click(ADMIN_ID, "quick_date:pending:today")
    edit = [r for r in harness.session.requests if type(r).__name__ == "EditMessageText"][-1]
    assert any(b.startswith("view_order_details:") for b in harness.buttons(edit))


async def test_saved_address_selection_and_location_button(harness, shop):
    """Regressions: select_saved_address raised TypeError; go_to_location had no handler."""
    pool = harness.pool
    await make_user(pool, CUSTOMER_ID)
    loc_id = await db.add_saved_location(pool, CUSTOMER_ID, "Uy", 41.31, 69.28, "Test address")

    await harness.click(CUSTOMER_ID, f"select_saved_address:{loc_id}")
    assert LEXICON["category_list_title"]["uz"] in harness.all_texts()
    ctx = harness.dp.fsm.get_context(harness.bot, chat_id=CUSTOMER_ID, user_id=CUSTOMER_ID)
    assert (await ctx.get_data())["session_lat"] == 41.31

    # someone else's saved address id is not usable
    await make_user(pool, 9999)
    harness.clear()
    await harness.click(9999, f"select_saved_address:{loc_id}")
    assert harness.last_answer().text == LEXICON["address_not_found"]["uz"]

    harness.clear()
    await harness.click(CUSTOMER_ID, "go_to_location")
    assert harness.sent_to(CUSTOMER_ID)[-1].text == LEXICON["ask_for_location"]["uz"]


async def test_two_variations_of_one_product_in_one_order(harness, shop):
    pool = harness.pool
    small = await db.add_product_variation(pool, shop, {"uz": "0.5"}, 20000)
    big = await db.add_product_variation(pool, shop, {"uz": "1.0"}, 35000)
    for var in (small, big):
        await harness.click(CUSTOMER_ID, f"customer_view_variation:{var}:0")
        await harness.click(CUSTOMER_ID, f"add_N_to_cart:variation:{var}")
    await harness.click(CUSTOMER_ID, "place_order")
    await harness.send(CUSTOMER_ID, "Ali")
    await harness.send_contact(CUSTOMER_ID, "+998901234567")
    await harness.send_location(CUSTOMER_ID, 41.31, 69.28)
    orders = await db.get_user_orders(pool, CUSTOMER_ID)
    assert len(orders) == 1 and orders[0]["total_amount"] == Decimal("55000.00")
