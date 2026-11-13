"""Harness for feeding real ``Update`` objects into the real Dispatcher.

The Bot uses :class:`MockedSession`, so no request ever leaves the process; every
Bot API call is recorded and can be asserted on.
"""

from __future__ import annotations

import itertools
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import asyncpg
import pytest
from aiogram import Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.methods import AnswerCallbackQuery, EditMessageText, SendMessage, SendPhoto, TelegramMethod
from aiogram.types import CallbackQuery, Chat, Contact, ErrorEvent, Location, Message, Update, User

from bot import build_dispatcher, create_bot
from core.config import Settings
from utils import geocoder


class MockedSession(BaseSession):
    def __init__(self) -> None:
        super().__init__()
        self.requests: list[TelegramMethod[Any]] = []
        self._ids = itertools.count(10_000)
        self._answered: set[str] = set()

    async def make_request(self, bot: Bot, method: TelegramMethod[Any], timeout: int | None = None) -> Any:  # noqa: ASYNC109 (BaseSession API)
        self.requests.append(method)
        if isinstance(method, AnswerCallbackQuery):
            # Behave like Telegram: a callback query can be answered only once.
            if method.callback_query_id in self._answered:
                raise TelegramBadRequest(method=method, message="query is too old or query ID is invalid")
            self._answered.add(method.callback_query_id)
        if isinstance(method, SendMessage | SendPhoto):
            return Message(
                message_id=next(self._ids),
                date=datetime.now(),
                chat=Chat(id=int(method.chat_id), type="private"),
                text=getattr(method, "text", None),
            )
        return True

    async def close(self) -> None:  # pragma: no cover - nothing to close
        pass

    async def stream_content(self, *args: Any, **kwargs: Any):  # pragma: no cover
        yield b""


@dataclass
class BotHarness:
    bot: Bot
    dp: Dispatcher
    pool: asyncpg.Pool
    settings: Settings
    session: MockedSession
    _update_ids: itertools.count = field(default_factory=lambda: itertools.count(1))
    _msg_ids: itertools.count = field(default_factory=lambda: itertools.count(1))

    # ── sending updates ─────────────────────────────────────
    @staticmethod
    def user(user_id: int) -> User:
        return User(id=user_id, is_bot=False, first_name=f"U{user_id}", language_code="uz")

    def _message(self, user_id: int, chat_id: int | None = None, **kw: Any) -> Message:
        chat_id = chat_id if chat_id is not None else user_id
        chat_type = "private" if chat_id > 0 else "supergroup"
        return Message(
            message_id=next(self._msg_ids),
            date=datetime.now(),
            chat=Chat(id=chat_id, type=chat_type),
            from_user=self.user(user_id),
            **kw,
        )

    async def send(self, user_id: int, text: str | None = None, *, chat_id: int | None = None, **kw: Any) -> Any:
        msg = self._message(user_id, chat_id, text=text, **kw)
        return await self.dp.feed_update(self.bot, Update(update_id=next(self._update_ids), message=msg))

    async def send_location(self, user_id: int, lat: float, lon: float) -> Any:
        return await self.send(user_id, location=Location(latitude=lat, longitude=lon))

    async def send_contact(self, user_id: int, phone: str) -> Any:
        return await self.send(user_id, contact=Contact(phone_number=phone, first_name="C", user_id=user_id))

    async def click(self, user_id: int, data: str, *, chat_id: int | None = None) -> Any:
        call = CallbackQuery(
            id=str(next(self._update_ids)),
            from_user=self.user(user_id),
            chat_instance="ci",
            data=data,
            message=self._message(self.bot.id, chat_id if chat_id is not None else user_id, text="old"),
        )
        return await self.dp.feed_update(self.bot, Update(update_id=next(self._update_ids), callback_query=call))

    # ── inspecting what the bot did ─────────────────────────
    def clear(self) -> None:
        self.session.requests.clear()

    def of_type(self, kind: type) -> list[Any]:
        return [r for r in self.session.requests if isinstance(r, kind)]

    def answers(self) -> list[AnswerCallbackQuery]:
        return self.of_type(AnswerCallbackQuery)

    def last_answer(self) -> AnswerCallbackQuery:
        answers = self.answers()
        assert answers, "the callback was never answered"
        return answers[-1]

    def sent_to(self, chat_id: int) -> list[SendMessage]:
        return [r for r in self.of_type(SendMessage) if int(r.chat_id) == chat_id]

    def all_texts(self) -> str:
        parts: list[str] = []
        for r in self.session.requests:
            for attr in ("text", "caption"):
                value = getattr(r, attr, None)
                if isinstance(value, str):
                    parts.append(value)
        return "\n".join(parts)

    def buttons(self, request: SendMessage | EditMessageText) -> list[str]:
        markup = request.reply_markup
        if markup is None or not hasattr(markup, "inline_keyboard"):
            return []
        return [b.callback_data or b.url or "" for row in markup.inline_keyboard for b in row]


@pytest.fixture
async def harness(db_pool: asyncpg.Pool, settings: Settings, monkeypatch) -> AsyncIterator[BotHarness]:
    async def no_network(lat: float, lon: float) -> str:
        return "Test address"

    monkeypatch.setattr(geocoder, "get_address_from_coords", no_network)
    monkeypatch.setattr("handlers.user_handlers.get_address_from_coords", no_network)

    session = MockedSession()
    bot = create_bot(settings, session=session)
    dp = build_dispatcher(settings, db_pool, MemoryStorage())

    # Production logs and swallows handler exceptions; tests must see them.
    errors: list[BaseException] = []

    async def record_error(event: ErrorEvent) -> bool:
        errors.append(event.exception)
        return True

    dp.errors.handlers.clear()
    dp.errors.register(record_error)
    h = BotHarness(bot=bot, dp=dp, pool=db_pool, settings=settings, session=session)
    try:
        yield h
        assert not errors, f"handlers raised: {errors!r}"
    finally:
        await dp.storage.close()
        # Routers are module-level singletons and may only have one parent:
        # detach them so the next test can build a fresh Dispatcher.
        for router in list(dp.sub_routers):
            router._parent_router = None
        dp.sub_routers.clear()
