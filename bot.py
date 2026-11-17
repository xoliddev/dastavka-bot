"""Entry point.

python bot.py           # run the bot (long polling)
python bot.py --check   # self-test: config, PostgreSQL (+ schema), Redis, routers; no Telegram calls
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

import asyncpg
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.base import BaseSession
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramUnauthorizedError
from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import ErrorEvent
from aiogram.utils.token import TokenValidationError, validate_token
from redis.asyncio import Redis

from core.config import Settings
from core.logging_config import setup_logging
from core.middlewares import ThrottleMiddleware, UserMiddleware
from core.telegram import AnswerCallbackOnce
from database_setup import apply_schema
from utils.geocoder import Geocoder, configure_geocoder, get_geocoder

logger = logging.getLogger("dastavka")


def create_bot(settings: Settings, session: BaseSession | None = None) -> Bot:
    bot = Bot(
        token=settings.bot_token.get_secret_value(),
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    bot.session.middleware(AnswerCallbackOnce())
    return bot


def build_dispatcher(
    settings: Settings, pool: asyncpg.Pool, storage: BaseStorage, *, throttle: ThrottleMiddleware | None = None
) -> Dispatcher:
    """Create a fully wired Dispatcher. Used by ``main`` and by the handler tests."""
    from handlers import admin, courier_handlers, customer_handlers, fallback, user_handlers
    from handlers.admin import group

    dp = Dispatcher(storage=storage, settings=settings, pool=pool)
    dp.update.outer_middleware(throttle or ThrottleMiddleware())
    dp.update.outer_middleware(UserMiddleware())
    dp.errors.register(on_error)

    # Order matters: public routers first, role-filtered routers next, fallback last.
    dp.include_routers(
        user_handlers.router,
        customer_handlers.router,
        group.router,
        admin.router,
        courier_handlers.router,
        fallback.router,
    )
    return dp


async def on_error(event: ErrorEvent) -> bool:
    update = event.update
    logger.error(
        "Unhandled error while processing update",
        extra={"update_id": update.update_id, "update_type": update.event_type},
        exc_info=event.exception,
    )
    return True


async def create_pool(settings: Settings) -> asyncpg.Pool:
    pool = await asyncpg.create_pool(
        dsn=settings.postgres_dsn,
        min_size=settings.db_pool_min_size,
        max_size=settings.db_pool_max_size,
    )
    async with pool.acquire() as conn:
        await apply_schema(conn)
    return pool


async def self_check(settings: Settings) -> int:
    """Boot everything up to (but excluding) Telegram authentication."""
    ok = True
    try:
        validate_token(settings.bot_token.get_secret_value())
        logger.info("check: BOT_TOKEN format ok")
    except TokenValidationError:
        logger.error("check: BOT_TOKEN is missing or malformed")
        ok = False
    if not settings.admin_ids:
        logger.warning("check: ADMIN_IDS is empty, nobody will be able to open the admin panel")

    pool = redis = None
    try:
        pool = await create_pool(settings)
        version = await pool.fetchval("SHOW server_version")
        logger.info("check: PostgreSQL ok, schema applied", extra={"server_version": version})

        redis = Redis.from_url(settings.redis_dsn)
        await redis.ping()
        logger.info("check: Redis ok")

        dp = build_dispatcher(settings, pool, RedisStorage(redis))
        logger.info("check: dispatcher built", extra={"update_types": ",".join(dp.resolve_used_update_types())})
    except Exception:
        logger.exception("check: failed")
        ok = False
    finally:
        if redis is not None:
            await redis.aclose()
        if pool is not None:
            await pool.close()

    logger.info("check: %s", "PASSED" if ok else "FAILED")
    return 0 if ok else 1


async def run(settings: Settings) -> None:
    configure_geocoder(
        Geocoder(
            user_agent=settings.nominatim_user_agent,
            url=settings.nominatim_url,
            min_interval=settings.nominatim_min_interval,
            cache_size=settings.geocoder_cache_size,
        )
    )
    pool = await create_pool(settings)
    redis = Redis.from_url(settings.redis_dsn)
    bot = create_bot(settings)
    dp = build_dispatcher(settings, pool, RedisStorage(redis))

    async def on_shutdown() -> None:
        # aiogram stops polling on SIGINT/SIGTERM, then runs this hook.
        logger.info("Shutting down: closing geocoder, Redis and PostgreSQL")
        await get_geocoder().close()
        await redis.aclose()
        await pool.close()

    dp.shutdown.register(on_shutdown)
    logger.info("Starting polling", extra={"admins": len(settings.admin_ids), "timezone": settings.timezone})
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        logger.info("Bot stopped")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dastavka food-delivery Telegram bot")
    parser.add_argument("--check", action="store_true", help="verify config, DB and Redis, then exit")
    args = parser.parse_args(argv)

    settings = Settings()
    setup_logging(settings.log_level, settings.log_format)
    if args.check:
        return asyncio.run(self_check(settings))
    try:
        asyncio.run(run(settings))
    except KeyboardInterrupt:  # Windows: Ctrl+C without signal handlers
        pass
    except TelegramUnauthorizedError:
        logger.error("Telegram rejected BOT_TOKEN (401 Unauthorized); check the token from @BotFather")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
