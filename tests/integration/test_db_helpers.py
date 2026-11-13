"""db_helpers against a real PostgreSQL 16."""

import asyncio
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal

import asyncpg
import pytest

import db_helpers as db
from tests.factories import make_courier, make_order, make_product, make_user

pytestmark = pytest.mark.integration


async def test_create_order_with_items(db_pool):
    _, prod_id = await make_product(db_pool, price="12000.00")
    order_id, daily_id = await make_order(db_pool, 1, prod_id, quantity=3, price="12000.00")

    order = await db.get_order(db_pool, order_id)
    assert daily_id == 1
    assert order["status"] == "pending"
    assert order["user_id"] == 1
    assert order["total_amount"] == Decimal("36000.00")
    items = await db.get_order_items_with_names(db_pool, order_id)
    assert [(i["quantity"], i["price_per_item"]) for i in items] == [(3, Decimal("12000.00"))]


async def test_order_can_contain_two_variations_of_one_product(db_pool):
    _, prod_id = await make_product(db_pool)
    small = await db.add_product_variation(db_pool, prod_id, {"uz": "Kichik"}, 10000)
    big = await db.add_product_variation(db_pool, prod_id, {"uz": "Katta"}, 15000)
    await make_user(db_pool, 1)
    items = [
        {"product_id": prod_id, "variation_id": small, "quantity": 1, "price_per_item": Decimal("10000")},
        {"product_id": prod_id, "variation_id": big, "quantity": 2, "price_per_item": Decimal("15000")},
    ]
    order_id, _ = await db.create_order(db_pool, 1, items, Decimal("40000"), "+998", 41.0, 69.0, "Ali")
    assert len(await db.get_order_items_with_names(db_pool, order_id)) == 2


async def test_daily_id_increments_and_resets(db_pool):
    _, prod_id = await make_product(db_pool)
    ids = [(await make_order(db_pool, 1, prod_id))[1] for _ in range(3)]
    assert ids == [1, 2, 3]

    await db.reset_daily_order_counter(db_pool)
    assert (await make_order(db_pool, 1, prod_id))[1] == 1
    assert (await make_order(db_pool, 1, prod_id))[1] == 2


async def test_concurrent_orders_get_unique_daily_ids(db_pool):
    _, prod_id = await make_product(db_pool)
    for uid in range(1, 11):
        await make_user(db_pool, uid)

    n = 60
    results = await asyncio.gather(*(make_order(db_pool, 1 + i % 10, prod_id) for i in range(n)))

    daily_ids = sorted(d for _, d in results)
    assert daily_ids == list(range(1, n + 1)), "daily_id must be unique and gap-free under concurrency"
    order_ids = {o for o, _ in results}
    assert len(order_ids) == n
    stored = await db_pool.fetch("SELECT daily_id FROM orders")
    assert sorted(r["daily_id"] for r in stored) == list(range(1, n + 1))


async def test_failed_order_does_not_burn_a_daily_id(db_pool):
    _, prod_id = await make_product(db_pool)
    await make_user(db_pool, 1)
    bad = [{"product_id": 999_999, "variation_id": None, "quantity": 1, "price_per_item": Decimal("1")}]
    with pytest.raises(asyncpg.ForeignKeyViolationError):  # FK violation → whole transaction rolled back
        await db.create_order(db_pool, 1, bad, Decimal("1"), "+998", 0, 0, "X")
    assert (await make_order(db_pool, 1, prod_id))[1] == 1


async def test_status_transitions_follow_state_machine(db_pool):
    _, prod_id = await make_product(db_pool)
    order_id, _ = await make_order(db_pool, 1, prod_id)

    # cannot skip straight to completed
    assert (
        await db.transition_order_status(db_pool, order_id, from_statuses=("delivering",), to_status="completed")
        is None
    )
    row = await db.transition_order_status(db_pool, order_id, from_statuses=("pending",), to_status="processing")
    assert row["status"] == "processing"
    # double click: the second accept does nothing
    assert (
        await db.transition_order_status(db_pool, order_id, from_statuses=("pending",), to_status="processing") is None
    )
    assert (await db.get_order(db_pool, order_id))["status"] == "processing"


async def test_invalid_transition_definition_raises(db_pool):
    with pytest.raises(ValueError):
        await db.transition_order_status(db_pool, 1, from_statuses=("completed",), to_status="pending")


async def test_transition_checks_owner(db_pool):
    _, prod_id = await make_product(db_pool)
    order_id, _ = await make_order(db_pool, 1, prod_id)
    await make_user(db_pool, 2)
    assert (
        await db.transition_order_status(db_pool, order_id, from_statuses=("pending",), to_status="canceled", user_id=2)
        is None
    )
    assert (await db.get_order(db_pool, order_id))["status"] == "pending"
    row = await db.transition_order_status(
        db_pool, order_id, from_statuses=("pending",), to_status="canceled", user_id=1
    )
    assert row["status"] == "canceled"


async def test_transition_respects_cancel_window(db_pool):
    _, prod_id = await make_product(db_pool)
    order_id, _ = await make_order(db_pool, 1, prod_id)
    await db_pool.execute("UPDATE orders SET created_at = now() - interval '10 minutes' WHERE id = $1", order_id)
    assert await db.transition_order_status(
        db_pool, order_id, from_statuses=("pending",), to_status="canceled", user_id=1,
        created_after=datetime.now(UTC) - timedelta(minutes=5),
    ) is None  # fmt: skip


async def test_assign_courier(db_pool):
    _, prod_id = await make_product(db_pool)
    order_id, _ = await make_order(db_pool, 1, prod_id)
    await make_courier(db_pool, 50)

    # not yet accepted → cannot assign
    assert not await db.assign_courier_to_order(db_pool, order_id, 50)
    await db.transition_order_status(db_pool, order_id, from_statuses=("pending",), to_status="processing")
    # unknown courier → rejected
    assert not await db.assign_courier_to_order(db_pool, order_id, 999)
    assert await db.assign_courier_to_order(db_pool, order_id, 50)

    order = await db.get_order(db_pool, order_id)
    assert (order["status"], order["courier_id"]) == ("delivering", 50)
    assert [o["id"] for o in await db.get_courier_active_orders(db_pool, 50)] == [order_id]
    statuses = {c["user_id"]: c["active_orders_count"] for c in await db.get_couriers_with_status(db_pool)}
    assert statuses == {50: 1}

    # only the assigned courier passes the courier_id guard
    assert (
        await db.transition_order_status(
            db_pool, order_id, from_statuses=("delivering",), to_status="completed", courier_id=51
        )
        is None
    )
    assert (
        await db.transition_order_status(
            db_pool, order_id, from_statuses=("delivering",), to_status="completed", courier_id=50
        )
        is not None
    )


async def test_inactive_courier_cannot_be_assigned(db_pool):
    _, prod_id = await make_product(db_pool)
    order_id, _ = await make_order(db_pool, 1, prod_id)
    await make_courier(db_pool, 50)
    await db.remove_courier(db_pool, 50)
    await db.transition_order_status(db_pool, order_id, from_statuses=("pending",), to_status="processing")
    assert not await db.assign_courier_to_order(db_pool, order_id, 50)


async def test_courier_remove_and_reactivate(db_pool):
    await make_courier(db_pool, 50)
    assert (await db.get_user(db_pool, 50))["role"] == "courier"
    await db.remove_courier(db_pool, 50)
    assert (await db.get_courier(db_pool, 50))["is_active"] is False
    assert (await db.get_user(db_pool, 50))["role"] == "customer"
    await db.reactivate_courier(db_pool, 50)
    assert (await db.get_courier(db_pool, 50))["is_active"] is True
    assert (await db.get_user(db_pool, 50))["role"] == "courier"


async def test_ensure_user_syncs_admin_role(db_pool):
    user = await db.ensure_user(db_pool, 7, "Ann", "ann", "ru", is_admin=True)
    assert user["role"] == "admin"
    assert user["selected_language_code"] == "uz"
    # removed from ADMIN_IDS → demoted
    user = await db.ensure_user(db_pool, 7, "Ann", "ann", "ru", is_admin=False)
    assert user["role"] == "customer"
    # courier role is kept for non-admins
    await make_courier(db_pool, 8)
    assert (await db.ensure_user(db_pool, 8, "Kuryer", None, "uz", is_admin=False))["role"] == "courier"
    # a demoted admin who is an active courier goes back to courier
    await db.set_user_role(db_pool, 8, "admin")
    assert (await db.ensure_user(db_pool, 8, "Kuryer", None, "uz", is_admin=False))["role"] == "courier"
    # name changes are stored
    assert (await db.ensure_user(db_pool, 8, "New", "nick", "uz", is_admin=False))["first_name"] == "New"


async def test_order_receivers_use_configured_admin_ids(db_pool):
    await make_user(db_pool, 1, role="admin")  # stale DB role, not in ADMIN_IDS
    await make_user(db_pool, 2)
    receivers = await db.get_order_receivers(db_pool, frozenset({2, 3}))
    assert [r["id"] for r in receivers] == [2]


async def test_orders_by_range_and_daily_report(db_pool):
    _, prod_id = await make_product(db_pool, price="10000.00", name="Somsa")
    o1, _ = await make_order(db_pool, 1, prod_id, quantity=2, price="10000.00")
    o2, _ = await make_order(db_pool, 1, prod_id, quantity=1, price="10000.00")
    for oid in (o1, o2):
        await db.update_order_status(db_pool, oid, "completed")
    # o2 happened "yesterday"
    await db_pool.execute("UPDATE orders SET created_at = now() - interval '2 days' WHERE id = $1", o2)

    now = datetime.now(UTC)
    start, end = now - timedelta(hours=1), now + timedelta(hours=1)
    rows = await db.get_orders_by_status_and_range(db_pool, "completed", start, end, 10, 0)
    assert [r["id"] for r in rows] == [o1]
    assert await db.count_orders_by_status_and_range(db_pool, "completed", start, end) == 1

    count, total, best = await db.get_daily_report(db_pool, start, end)
    assert count == 1
    assert total == Decimal("20000.00")
    assert "Somsa" in best


async def test_cafe_settings_roundtrip(db_pool):
    await db.update_cafe_location(db_pool, 41.3, 69.2)
    await db.update_cafe_radius(db_pool, 7.5)
    await db.update_work_hours(db_pool, time(18), time(3))
    await db.update_order_buffer(db_pool, 20)
    await db.update_cancel_window(db_pool, 10)
    s = await db.get_cafe_settings(db_pool)
    assert (s["latitude"], s["longitude"], s["delivery_radius_km"]) == (41.3, 69.2, Decimal("7.50"))
    assert (s["work_hours_start"], s["work_hours_end"]) == (time(18), time(3))
    assert (s["order_acceptance_buffer_minutes"], s["cancel_window_minutes"]) == (20, 10)
