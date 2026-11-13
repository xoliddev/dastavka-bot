import pytest
from pydantic import ValidationError

from core.config import DEFAULT_USER_AGENT, Settings


def test_defaults():
    s = Settings(_env_file=None)
    assert s.timezone == "Asia/Tashkent"
    assert s.tz.key == "Asia/Tashkent"
    assert s.admin_ids == frozenset()
    assert s.notification_group_id is None
    assert s.nominatim_user_agent == DEFAULT_USER_AGENT
    assert "YourBotName" not in s.nominatim_user_agent
    assert s.nominatim_min_interval == 1.0


def test_env_parsing(monkeypatch):
    monkeypatch.setenv("ADMIN_IDS", " 111, 222 ,,333")
    monkeypatch.setenv("NOTIFICATION_GROUP_ID", "")
    monkeypatch.setenv("TIMEZONE", "Europe/Moscow")
    monkeypatch.setenv("NOMINATIM_USER_AGENT", "my-cafe-bot/1.0 (ops@example.com)")
    s = Settings(_env_file=None)
    assert s.admin_ids == frozenset({111, 222, 333})
    assert s.notification_group_id is None
    assert s.tz.key == "Europe/Moscow"
    assert s.nominatim_user_agent == "my-cafe-bot/1.0 (ops@example.com)"


def test_group_id_parsed(monkeypatch):
    monkeypatch.setenv("NOTIFICATION_GROUP_ID", "-1001234567890")
    assert Settings(_env_file=None).notification_group_id == -1001234567890


def test_invalid_admin_ids_rejected():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, admin_ids="12,abc")


def test_invalid_timezone_rejected():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, timezone="Mars/Olympus")


def test_blank_user_agent_falls_back_to_default():
    assert Settings(_env_file=None, nominatim_user_agent="  ").nominatim_user_agent == DEFAULT_USER_AGENT


def test_dsn_from_parts_escapes_password():
    s = Settings(
        _env_file=None,
        postgres_user="bot",
        postgres_password="p@ss:w/rd",
        postgres_host="db",
        postgres_port=5433,
        postgres_db="cafe",
    )
    assert s.postgres_dsn == "postgresql://bot:p%40ss%3Aw%2Frd@db:5433/cafe"


def test_database_url_wins():
    s = Settings(_env_file=None, database_url="postgresql://a:b@h/d", postgres_host="ignored")
    assert s.postgres_dsn == "postgresql://a:b@h/d"


def test_redis_dsn():
    assert Settings(_env_file=None, redis_host="redis", redis_db=2).redis_dsn == "redis://redis:6379/2"
    assert Settings(_env_file=None, redis_url="redis://x:1/0").redis_dsn == "redis://x:1/0"
