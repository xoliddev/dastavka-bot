"""Typed application settings loaded from environment variables / ``.env``."""

from __future__ import annotations

from functools import cached_property
from typing import Annotated, Literal
from urllib.parse import quote
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

DEFAULT_USER_AGENT = "dastavka-bot/2.0 (+https://github.com/xoliddev/dastavka-bot)"


class Settings(BaseSettings):
    """All runtime configuration. Every field maps to an upper-case env var."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── Telegram ────────────────────────────────────────────
    bot_token: SecretStr = SecretStr("")
    admin_ids: Annotated[frozenset[int], NoDecode] = frozenset()
    notification_group_id: int | None = None

    # ── PostgreSQL ──────────────────────────────────────────
    database_url: str | None = None
    postgres_user: str = "dastavka"
    postgres_password: SecretStr = SecretStr("")
    postgres_db: str = "dastavka"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    db_pool_min_size: int = 1
    db_pool_max_size: int = 10

    # ── Redis (FSM storage) ─────────────────────────────────
    redis_url: str | None = None
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    # ── Business / integrations ─────────────────────────────
    timezone: str = "Asia/Tashkent"
    nominatim_url: str = "https://nominatim.openstreetmap.org/reverse"
    nominatim_user_agent: str = DEFAULT_USER_AGENT
    nominatim_min_interval: float = Field(default=1.0, ge=0)
    geocoder_cache_size: int = Field(default=1024, ge=0)

    # ── Logging ─────────────────────────────────────────────
    log_level: str = "INFO"
    log_format: Literal["json", "text"] = "text"

    @field_validator("admin_ids", mode="before")
    @classmethod
    def _parse_admin_ids(cls, value: object) -> object:
        if value is None:
            return frozenset()
        if isinstance(value, int):
            return frozenset({value})
        if isinstance(value, str):
            parts = [p.strip() for p in value.replace(";", ",").split(",")]
            ids = set()
            for part in parts:
                if not part:
                    continue
                if not part.lstrip("-").isdigit():
                    raise ValueError(f"ADMIN_IDS must contain integers, got {part!r}")
                ids.add(int(part))
            return frozenset(ids)
        return value

    @field_validator("notification_group_id", mode="before")
    @classmethod
    def _empty_group_is_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("database_url", "redis_url", mode="before")
    @classmethod
    def _empty_url_is_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("timezone")
    @classmethod
    def _valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"Unknown TIMEZONE {value!r}") from exc
        return value

    @field_validator("nominatim_user_agent")
    @classmethod
    def _non_empty_user_agent(cls, value: str) -> str:
        return value.strip() or DEFAULT_USER_AGENT

    # ── Derived values ──────────────────────────────────────
    @cached_property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    @property
    def postgres_dsn(self) -> str:
        if self.database_url:
            return self.database_url
        password = quote(self.postgres_password.get_secret_value(), safe="")
        user = quote(self.postgres_user, safe="")
        return f"postgresql://{user}:{password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def redis_dsn(self) -> str:
        if self.redis_url:
            return self.redis_url
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    def is_admin(self, user_id: int | None) -> bool:
        return user_id is not None and user_id in self.admin_ids


def get_settings() -> Settings:
    return Settings()
