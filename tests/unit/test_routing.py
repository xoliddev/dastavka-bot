"""Structural guards: every admin/courier handler sits behind its role filter."""

import importlib
import pkgutil

from aiogram import Router

import handlers.admin as admin_pkg
from core.filters import IsAdmin, IsCourier
from handlers import courier_handlers


def _root_filters(router: Router, event: str) -> list[type]:
    observer = router.observers[event]
    return [type(f.callback) for f in observer._handler.filters or []]


def test_admin_router_has_admin_filter_on_messages_and_callbacks():
    for event in ("message", "callback_query"):
        assert IsAdmin in _root_filters(admin_pkg.router, event)


def test_courier_router_has_courier_filter():
    for event in ("message", "callback_query"):
        assert IsCourier in _root_filters(courier_handlers.router, event)


def test_every_admin_module_router_is_behind_the_admin_filter():
    included = set(map(id, admin_pkg.router.sub_routers))
    public = {"handlers.admin.group"}  # /set_group must answer non-admins itself
    for info in pkgutil.iter_modules(admin_pkg.__path__):
        name = f"{admin_pkg.__name__}.{info.name}"
        module = importlib.import_module(name)
        router = getattr(module, "router", None)
        if router is None or name in public:
            continue
        assert id(router) in included, f"{name}.router is not included in the IsAdmin-filtered admin router"


def test_no_duplicate_callback_handlers():
    """Two handlers with the same function name in one router (the old fsm_courier_id bug)."""
    routers = [*admin_pkg.router.sub_routers, courier_handlers.router]
    for router in routers:
        for event in ("message", "callback_query"):
            names = [h.callback.__name__ for h in router.observers[event].handlers]
            dupes = {n for n in names if names.count(n) > 1}
            assert not dupes, f"{router.name}: duplicate {event} handlers {dupes}"
