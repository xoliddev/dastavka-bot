"""Every callback_data the code can produce must be routed to a real handler.

The old pagination buttons (``customer_view_cat_page:``, ``subcategory_page:N``,
``courier_page:``) rendered fine but matched no handler, so pressing them only
hit the catch-all. This test closes that class of bug:

1. Statically collect every callback_data template from ``handlers/`` and
   ``utils/keyboards.py`` (``callback_data=``, ``back_callback_data=``,
   ``page_callback=`` lambdas, ``callback_prefix=`` of pagination keyboards, ...).
2. Turn each template into a concrete sample (``f"x:{id}:{page}"`` → ``"x:1:1"``).
3. Check that at least one handler, other than the catch-all fallback, accepts it.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from aiogram import Router
from aiogram.types import CallbackQuery, User

ROOT = Path(__file__).resolve().parents[2]
SOURCES = [*sorted((ROOT / "handlers").rglob("*.py")), ROOT / "utils" / "keyboards.py"]

CALLBACK_KEYWORDS = {"callback_data", "back_callback_data", "back_callback", "page_callback"}
PREFIX_NAMES = {"callback_prefix"}


def _is_callback_name(name: str) -> bool:
    return (
        name in CALLBACK_KEYWORDS or name == "back_cb" or (name.endswith("callback_data") and name != "callback_data_")
    )


def _templates(node: ast.AST) -> list[ast.AST]:
    """String constants and f-strings inside an expression (f-strings are not split)."""
    found: list[ast.AST] = []

    def visit(n: ast.AST) -> None:
        if isinstance(n, ast.JoinedStr) or (isinstance(n, ast.Constant) and isinstance(n.value, str)):
            found.append(n)
            return
        if isinstance(n, ast.Subscript | ast.Compare | ast.BoolOp):  # dict keys / conditions, not values
            return
        if isinstance(n, ast.IfExp):
            visit(n.body)
            visit(n.orelse)
            return
        for child in ast.iter_child_nodes(n):
            visit(child)

    visit(node)
    return found


def _sample(node: ast.AST) -> str | None:
    """Concrete example of a template; None when the prefix itself is dynamic."""
    if isinstance(node, ast.Constant):
        return node.value
    assert isinstance(node, ast.JoinedStr)
    if not node.values or isinstance(node.values[0], ast.FormattedValue):
        return None
    return "".join(v.value if isinstance(v, ast.Constant) else "1" for v in node.values)


def collect_samples() -> dict[str, str]:
    """sample callback_data → "file:line" where it is produced."""
    samples: dict[str, str] = {}

    def add(node: ast.AST, origin: str, *, prefix: bool = False) -> None:
        for tpl in _templates(node):
            sample = _sample(tpl)
            if sample is None:
                continue
            if prefix:
                sample = f"{sample}:1:0"  # build_pagination_keyboard: f"{prefix}:{item_id}:{page}"
            samples.setdefault(sample, f"{origin}:{tpl.lineno}")

    for path in SOURCES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        origin = str(path.relative_to(ROOT)).replace("\\", "/")
        for node in ast.walk(tree):
            if isinstance(node, ast.keyword) and node.arg:
                if node.arg in PREFIX_NAMES:
                    add(node.value, origin, prefix=True)
                elif node.arg in CALLBACK_KEYWORDS:
                    add(node.value, origin)
            elif isinstance(node, ast.Assign | ast.AnnAssign):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    name = getattr(target, "id", None) or getattr(target, "attr", None)
                    if not name or node.value is None:
                        continue
                    if name in PREFIX_NAMES:
                        add(node.value, origin, prefix=True)
                    elif _is_callback_name(name):
                        add(node.value, origin)
            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                args = node.args.args[len(node.args.args) - len(node.args.defaults) :]
                for arg, default in zip(args, node.args.defaults, strict=True):
                    if _is_callback_name(arg.arg):
                        add(default, origin)
    return samples


def _all_routers() -> list[Router]:
    from handlers import admin, courier_handlers, customer_handlers, fallback, user_handlers
    from handlers.admin import group

    result: list[Router] = []

    def walk(router: Router) -> None:
        result.append(router)
        for sub in router.sub_routers:
            walk(sub)

    for router in (user_handlers.router, customer_handlers.router, group.router, admin.router,
                   courier_handlers.router, fallback.router):  # fmt: skip
        walk(router)
    return result


async def _matching_handlers(data: str) -> list[str]:
    call = CallbackQuery(id="1", from_user=User(id=1, is_bot=False, first_name="T"), chat_instance="c", data=data)
    matches = []
    for router in _all_routers():
        for handler in router.observers["callback_query"].handlers:
            if not handler.filters:  # the catch-all in handlers/fallback.py does not count
                continue
            ok, _ = await handler.check(call, raw_state=None)
            if ok:
                matches.append(f"{router.name}.{handler.callback.__name__}")
    return matches


SAMPLES = collect_samples()


def test_collector_sees_the_keyboards():
    # sanity: the static scan really found the callback data (including pagination)
    assert len(SAMPLES) > 80
    for expected in (
        "customer_page:1",
        "customer_cat_page:1:1:1",
        "category_page:1",
        "subcategory_page:1:1",
        "product_page:1:1",
        "courier_page:1",
        "my_active_deliveries_page:1",
        "orders_by_status_page:1:1",
        "customer_view_cat:1:0",
        "view_delivery_task:1:0",
        "noop",
    ):
        assert expected in SAMPLES, expected


@pytest.mark.parametrize("data", sorted(SAMPLES))
async def test_callback_data_has_a_handler(data):
    assert len(data.encode()) <= 64  # Telegram limit for callback_data
    matches = await _matching_handlers(data)
    assert matches, f"callback_data {data!r} produced at {SAMPLES[data]} has no handler"


def test_legacy_page_callbacks_are_no_longer_produced():
    for dead in ("customer_view_cat_page:1", "courier_page:1:1", "view_delivery_task_page:1", "subcategory_page:1"):
        assert dead not in SAMPLES
