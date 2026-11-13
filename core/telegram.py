"""Bot API request middlewares."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

from aiogram import Bot
from aiogram.client.session.middlewares.base import BaseRequestMiddleware, NextRequestMiddlewareType
from aiogram.methods import AnswerCallbackQuery, TelegramMethod


class AnswerCallbackOnce(BaseRequestMiddleware):
    """Drop repeated ``answerCallbackQuery`` calls for the same query id.

    Several handlers show an alert (``call.answer(text, show_alert=True)``) and then
    re-render a menu through a shared helper that answers the query again. Telegram
    rejects the second answer with "query is too old", which used to surface as an
    error after the work was done. The first answer (the meaningful one) wins.
    """

    def __init__(self, max_size: int = 4096) -> None:
        self._seen: OrderedDict[str, None] = OrderedDict()
        self._max_size = max_size

    async def __call__(
        self,
        make_request: NextRequestMiddlewareType[Any],
        bot: Bot,
        method: TelegramMethod[Any],
    ) -> Any:
        if isinstance(method, AnswerCallbackQuery):
            if method.callback_query_id in self._seen:
                return True
            self._seen[method.callback_query_id] = None
            while len(self._seen) > self._max_size:
                self._seen.popitem(last=False)
        return await make_request(bot, method)
