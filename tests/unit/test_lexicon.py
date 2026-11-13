import re
import string
from pathlib import Path

import pytest

from db_helpers import ORDER_TRANSITIONS
from locales.lexicon import LEXICON
from utils.lexicon_utils import SUPPORTED_LANGUAGES, get_i18n_name, get_text

ROOT = Path(__file__).resolve().parents[2]
SOURCES = [p for d in ("handlers", "utils", "core") for p in (ROOT / d).rglob("*.py")]
KEY_RE = re.compile(r"""get_text\(\s*["']([A-Za-z0-9_]+)["']""")
# Keys passed indirectly (e.g. alert_key="...", text_key="..." helpers).
INDIRECT_RE = re.compile(r"""\b\w*_key\s*=\s*["']([A-Za-z0-9_]+)["']""")


def _placeholders(text: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


def _used_keys() -> set[str]:
    keys: set[str] = set()
    for path in SOURCES:
        src = path.read_text(encoding="utf-8")
        keys |= set(KEY_RE.findall(src))
        keys |= set(INDIRECT_RE.findall(src))
    return keys


@pytest.mark.parametrize("key", sorted(LEXICON))
def test_every_key_has_all_languages(key):
    entry = LEXICON[key]
    missing = [lang for lang in SUPPORTED_LANGUAGES if not (entry.get(lang) or "").strip()]
    assert not missing, f"{key!r} is missing translations: {missing}"


@pytest.mark.parametrize("key", sorted(LEXICON))
def test_placeholders_match_across_languages(key):
    entry = LEXICON[key]
    reference = _placeholders(entry["uz"])
    for lang in SUPPORTED_LANGUAGES:
        assert _placeholders(entry[lang]) == reference, f"{key!r}/{lang} placeholders differ from 'uz'"


def test_every_key_used_in_code_exists():
    missing = sorted(k for k in _used_keys() if k not in LEXICON)
    assert not missing, f"keys used in code but absent from LEXICON: {missing}"


@pytest.mark.parametrize("status", sorted(ORDER_TRANSITIONS))
def test_every_order_status_has_a_label(status):
    assert f"status_{status}" in LEXICON


def test_get_text_falls_back_to_uzbek_then_key():
    lexicon = {"only_uz": {"uz": "salom"}}
    assert get_text("only_uz", "ru", lexicon) == "salom"
    assert get_text("unknown_key", "en", lexicon) == "unknown_key"


def test_get_i18n_name_fallbacks():
    assert get_i18n_name('{"uz": "Osh", "ru": "Плов"}', "ru") == "Плов"
    assert get_i18n_name('{"uz": "Osh", "en": "Pilaf"}', "ru") == "Pilaf"
    assert get_i18n_name('{"uz": "Osh"}', "ru") == "Osh"
    assert get_i18n_name('{"de": "Reis"}', "ru") == "Reis"
    assert get_i18n_name("not json", "uz") == "Nomsiz"
