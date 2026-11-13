# handlers/admin/common.py
"""Admin modullari uchun umumiy yordamchi funksiyalar."""

from __future__ import annotations

import json

import asyncpg

from locales.lexicon import LEXICON

# Barcha admin matnlari shu lug'atdan olinadi.
I18N: dict[str, dict[str, str]] = LEXICON


def _lang(user) -> str:
    """Foydalanuvchi tilini aniqlaydi."""
    if not user:
        return "uz"
    return user.get("selected_language_code") or user.get("language_code") or "uz"


def _i18n_value(raw: str | dict, lang: str) -> str:
    names = raw if isinstance(raw, dict) else json.loads(raw)
    return names.get(lang) or next(iter(names.values()), "")


def _cat_name(rec: asyncpg.Record, lang: str) -> str:
    """JSONB dan kategoriya nomini oladi."""
    return _i18n_value(rec["name"], lang)


def _prod_name(rec: asyncpg.Record, lang: str) -> str:
    """JSONB dan mahsulot nomini oladi."""
    return _i18n_value(rec["name"], lang)


def parse_int_arg(data: str | None, index: int = 1) -> int | None:
    """``"prefix:12:0"`` → 12. Noto'g'ri (soxta) callback ma'lumotida ``None`` qaytaradi."""
    try:
        return int((data or "").split(":")[index])
    except (IndexError, ValueError):
        return None
