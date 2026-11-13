"""Admin panel.

Every sub-router is attached to :data:`router`, which carries the ``IsAdmin``
filter for messages *and* callback queries. A handler in this package can
therefore never run for a non-admin, no matter what callback data is sent.

``/set_group`` lives in :mod:`handlers.admin.group` outside this filter on
purpose: it must answer non-admins with an explanatory error.
"""

from aiogram import Router

from core.filters import IsAdmin
from handlers.admin import categories, menu, orders, products, settings, team, variations

router = Router(name="admin")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

router.include_routers(
    menu.router,
    categories.router,
    products.router,
    variations.router,
    orders.router,
    settings.router,
    team.router,
)

__all__ = ["router"]
