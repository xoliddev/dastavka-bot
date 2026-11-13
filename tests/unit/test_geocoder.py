"""Geocoder: Nominatim policy compliance (User-Agent, 1 req/s, caching) without network."""

import asyncio

import pytest

from utils.geocoder import Geocoder


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def make_geocoder(clock: FakeClock, **kw) -> tuple[Geocoder, list[tuple[float, float]]]:
    calls: list[tuple[float, float]] = []
    geocoder = Geocoder(clock=clock, sleep=clock.sleep, **kw)

    async def fake_fetch(lat: float, lon: float) -> str:
        calls.append((lat, lon))
        return f"addr {lat},{lon}"

    geocoder._fetch = fake_fetch  # type: ignore[method-assign]
    return geocoder, calls


async def test_cache_hit_does_not_call_api():
    clock = FakeClock()
    geo, calls = make_geocoder(clock)
    assert await geo.reverse(41.3, 69.2) == "addr 41.3,69.2"
    assert await geo.reverse(41.3, 69.2) == "addr 41.3,69.2"
    # nearly the same point (sub-metre difference) shares the cache entry
    assert await geo.reverse(41.300001, 69.200001) == "addr 41.3,69.2"
    assert calls == [(41.3, 69.2)]


async def test_rate_limit_one_request_per_second():
    clock = FakeClock()
    geo, calls = make_geocoder(clock, min_interval=1.0)
    await geo.reverse(1.0, 1.0)
    clock.now += 0.25
    await geo.reverse(2.0, 2.0)  # must wait the remaining 0.75 s
    await geo.reverse(3.0, 3.0)  # must wait a full second
    assert clock.sleeps == pytest.approx([0.75, 1.0])
    assert len(calls) == 3


async def test_no_wait_after_interval_elapsed():
    clock = FakeClock()
    geo, _ = make_geocoder(clock, min_interval=1.0)
    await geo.reverse(1.0, 1.0)
    clock.now += 5
    await geo.reverse(2.0, 2.0)
    assert clock.sleeps == []


async def test_concurrent_requests_are_serialised():
    clock = FakeClock()
    geo, calls = make_geocoder(clock, min_interval=1.0)
    await asyncio.gather(*(geo.reverse(float(i), 0.0) for i in range(4)))
    assert len(calls) == 4
    assert clock.sleeps == pytest.approx([1.0, 1.0, 1.0])


async def test_concurrent_same_point_fetched_once():
    clock = FakeClock()
    geo, calls = make_geocoder(clock)
    results = await asyncio.gather(*(geo.reverse(5.0, 5.0) for _ in range(5)))
    assert set(results) == {"addr 5.0,5.0"}
    assert len(calls) == 1


async def test_cache_is_bounded_lru():
    clock = FakeClock()
    geo, calls = make_geocoder(clock, cache_size=2, min_interval=0)
    await geo.reverse(1.0, 1.0)
    await geo.reverse(2.0, 2.0)
    await geo.reverse(1.0, 1.0)  # refresh 1 → 2 becomes the oldest
    await geo.reverse(3.0, 3.0)  # evicts 2
    await geo.reverse(1.0, 1.0)
    await geo.reverse(2.0, 2.0)
    assert calls == [(1.0, 1.0), (2.0, 2.0), (3.0, 3.0), (2.0, 2.0)]


async def test_errors_return_none_and_are_not_cached():
    clock = FakeClock()
    geo = Geocoder(clock=clock, sleep=clock.sleep, min_interval=0)
    attempts = 0

    async def flaky(lat, lon):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise OSError("network down")
        return "ok"

    geo._fetch = flaky  # type: ignore[method-assign]
    assert await geo.reverse(1.0, 1.0) is None
    assert await geo.reverse(1.0, 1.0) == "ok"


async def test_user_agent_is_sent(monkeypatch):
    """The real _fetch sets the configured User-Agent on the aiohttp session."""
    captured = {}

    class FakeResp:
        status = 200

        async def json(self):
            return {"display_name": "Tashkent"}

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

    class FakeSession:
        closed = False

        def __init__(self, headers=None, timeout=None):
            captured["headers"] = headers

        def get(self, url, params=None):
            captured["url"], captured["params"] = url, params
            return FakeResp()

        async def close(self):
            self.closed = True

    monkeypatch.setattr("utils.geocoder.aiohttp.ClientSession", FakeSession)
    geo = Geocoder(user_agent="cafe-bot/9 (ops@example.com)", url="https://nominatim.example/reverse")
    assert await geo.reverse(41.3, 69.2) == "Tashkent"
    assert captured["headers"]["User-Agent"] == "cafe-bot/9 (ops@example.com)"
    assert captured["url"] == "https://nominatim.example/reverse"
    assert captured["params"]["format"] == "jsonv2"
    await geo.close()
