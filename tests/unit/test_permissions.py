"""Unit tests for the role filters and per-object ownership predicates."""

from contextlib import asynccontextmanager

import pytest
from aiogram.types import User

from core.config import Settings
from core.filters import IsAdmin, IsCourier, is_active_courier, is_admin_user, is_assigned_courier, is_order_owner
from db_helpers import can_transition


def _user(uid: int) -> User:
    return User(id=uid, is_bot=False, first_name="T")


@pytest.fixture
def cfg() -> Settings:
    return Settings(_env_file=None, admin_ids="10, 20")


class FakePool:
    """Minimal stand-in for asyncpg.Pool used by db_helpers.get_courier."""

    def __init__(self, couriers: dict[int, dict]):
        self.couriers = couriers

    @asynccontextmanager
    async def acquire(self):
        yield self

    async def fetchrow(self, query, user_id):
        assert "FROM couriers" in query
        return self.couriers.get(user_id)


async def test_is_admin_filter(cfg):
    f = IsAdmin()
    assert await f(object(), settings=cfg, event_from_user=_user(10))
    assert await f(object(), settings=cfg, event_from_user=_user(20))
    assert not await f(object(), settings=cfg, event_from_user=_user(30))
    assert not await f(object(), settings=cfg, event_from_user=None)


def test_admin_is_decided_by_config_not_db_role(cfg):
    # A stale DB role must not matter: only ADMIN_IDS grants admin.
    assert is_admin_user(_user(10), cfg)
    assert not is_admin_user(_user(99), cfg)


def test_empty_admin_ids_means_nobody_is_admin():
    assert not is_admin_user(_user(10), Settings(_env_file=None, admin_ids=""))


async def test_is_courier_requires_role_and_active_record():
    pool = FakePool({1: {"user_id": 1, "is_active": True}, 2: {"user_id": 2, "is_active": False}})
    f = IsCourier()
    assert await f(object(), pool=pool, db_user={"id": 1, "role": "courier"})
    # deactivated courier
    assert not await f(object(), pool=pool, db_user={"id": 2, "role": "courier"})
    # role says courier but no couriers row
    assert not await f(object(), pool=pool, db_user={"id": 3, "role": "courier"})
    # active courier row but role was reset to customer
    assert not await is_active_courier(pool, {"id": 1, "role": "customer"})
    assert not await f(object(), pool=pool, db_user=None)


def test_order_ownership():
    order = {"id": 5, "user_id": 100, "courier_id": 7}
    assert is_order_owner(order, 100)
    assert not is_order_owner(order, 101)
    assert not is_order_owner(None, 100)


def test_assigned_courier():
    order = {"id": 5, "user_id": 100, "courier_id": 7}
    assert is_assigned_courier(order, 7)
    assert not is_assigned_courier(order, 8)
    assert not is_assigned_courier({"id": 6, "user_id": 1, "courier_id": None}, 7)
    assert not is_assigned_courier(None, 7)


@pytest.mark.parametrize(
    ("src", "dst", "ok"),
    [
        ("pending", "processing", True),
        ("pending", "canceled", True),
        ("processing", "delivering", True),
        ("delivering", "completed", True),
        ("delivering", "disputed", True),
        ("disputed", "completed", True),
        ("pending", "completed", False),
        ("pending", "delivering", False),
        ("completed", "pending", False),
        ("canceled", "processing", False),
        ("delivering", "canceled", False),
    ],
)
def test_order_state_machine(src, dst, ok):
    assert can_transition(src, dst) is ok
