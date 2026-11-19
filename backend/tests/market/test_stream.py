"""Tests for the SSE streaming generator and router factory."""

import json

from app.market.cache import PriceCache
from app.market.stream import _generate_events, create_stream_router


class FakeRequest:
    """Minimal stand-in for starlette Request; disconnects after N checks."""

    client = None

    def __init__(self, connected_checks: int) -> None:
        self._remaining = connected_checks

    async def is_disconnected(self) -> bool:
        if self._remaining <= 0:
            return True
        self._remaining -= 1
        return False


async def _collect(cache: PriceCache, checks: int) -> list[str]:
    return [e async for e in _generate_events(cache, FakeRequest(checks), interval=0)]


class TestGenerateEvents:
    async def test_first_event_is_retry_directive(self):
        events = await _collect(PriceCache(), 0)
        assert events == ["retry: 1000\n\n"]

    async def test_emits_prices_payload(self):
        cache = PriceCache()
        cache.update("AAPL", 190.0)
        cache.update("GOOGL", 175.0)
        events = await _collect(cache, 1)
        assert len(events) == 2
        assert events[1].startswith("data: ") and events[1].endswith("\n\n")
        payload = json.loads(events[1][len("data: "):])
        assert set(payload) == {"AAPL", "GOOGL"}
        assert payload["AAPL"]["price"] == 190.0
        assert payload["AAPL"]["direction"] == "flat"

    async def test_unchanged_cache_not_resent(self):
        cache = PriceCache()
        cache.update("AAPL", 190.0)
        events = await _collect(cache, 3)
        assert sum(e.startswith("data: ") for e in events) == 1

    async def test_empty_cache_sends_no_data(self):
        events = await _collect(PriceCache(), 2)
        assert not any(e.startswith("data: ") for e in events)


class TestRouter:
    def test_prices_route_registered(self):
        router = create_stream_router(PriceCache())
        assert "/api/stream/prices" in [r.path for r in router.routes]

    def test_calling_factory_twice_does_not_duplicate_routes(self):
        cache = PriceCache()
        create_stream_router(cache)
        router = create_stream_router(cache)
        assert [r.path for r in router.routes].count("/api/stream/prices") == 1
