"""Reverse geocoding via Nominatim (OpenStreetMap) with throttling and caching.

Nominatim's usage policy (https://operations.osmfoundation.org/policies/nominatim/)
requires an identifying User-Agent, at most 1 request per second and caching of
results. All three are handled here.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable

import aiohttp

from core.config import DEFAULT_USER_AGENT

logger = logging.getLogger(__name__)

DEFAULT_URL = "https://nominatim.openstreetmap.org/reverse"
# ~1 m precision: nearby taps of the same spot share one cache entry.
_COORD_PRECISION = 5

Fetcher = Callable[[float, float], Awaitable[str | None]]


class Geocoder:
    def __init__(
        self,
        *,
        user_agent: str = DEFAULT_USER_AGENT,
        url: str = DEFAULT_URL,
        min_interval: float = 1.0,
        cache_size: int = 1024,
        timeout: float = 10.0,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.user_agent = user_agent
        self.url = url
        self.min_interval = min_interval
        self.cache_size = cache_size
        self.timeout = timeout
        self._clock = clock
        self._sleep = sleep
        self._cache: OrderedDict[tuple[float, float], str | None] = OrderedDict()
        self._lock = asyncio.Lock()
        self._last_request: float | None = None
        self._session: aiohttp.ClientSession | None = None

    # ── public API ──────────────────────────────────────────
    async def reverse(self, latitude: float, longitude: float) -> str | None:
        key = (round(latitude, _COORD_PRECISION), round(longitude, _COORD_PRECISION))
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]

        async with self._lock:
            # Another task may have filled the cache while we were waiting.
            if key in self._cache:
                return self._cache[key]
            await self._throttle()
            try:
                address = await self._fetch(*key)
            except Exception:  # network errors must never break the order flow
                logger.warning("Reverse geocoding failed", extra={"lat": key[0], "lon": key[1]}, exc_info=True)
                return None
            finally:
                self._last_request = self._clock()
            self._remember(key, address)
            return address

    async def close(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()
        self._session = None

    # ── internals ───────────────────────────────────────────
    async def _throttle(self) -> None:
        if self._last_request is None or self.min_interval <= 0:
            return
        wait = self.min_interval - (self._clock() - self._last_request)
        if wait > 0:
            await self._sleep(wait)

    def _remember(self, key: tuple[float, float], address: str | None) -> None:
        if self.cache_size <= 0:
            return
        self._cache[key] = address
        self._cache.move_to_end(key)
        while len(self._cache) > self.cache_size:
            self._cache.popitem(last=False)

    async def _fetch(self, latitude: float, longitude: float) -> str | None:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"User-Agent": self.user_agent},
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            )
        params = {"lat": latitude, "lon": longitude, "format": "jsonv2", "addressdetails": 0}
        async with self._session.get(self.url, params=params) as resp:
            if resp.status != 200:
                logger.warning("Nominatim returned HTTP %s", resp.status)
                return None
            data = await resp.json()
            return data.get("display_name")


_default = Geocoder()


def configure_geocoder(geocoder: Geocoder) -> None:
    """Replace the module-level geocoder (called once on startup, or from tests)."""
    global _default
    _default = geocoder


def get_geocoder() -> Geocoder:
    return _default


async def get_address_from_coords(latitude: float, longitude: float) -> str | None:
    """Backwards-compatible helper used by the handlers."""
    return await _default.reverse(latitude, longitude)
