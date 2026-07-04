"""Integration + lifecycle tests for the OpenAPI wrapper server."""

from __future__ import annotations

import httpx

from openapi_mcp._server_deps import aclose_client_sync, make_server_lifespan


async def test_lifespan_closes_client() -> None:
    """The lifespan closes the upstream client exactly once on exit."""
    client = httpx.AsyncClient()
    lifespan = make_server_lifespan(client)
    async with lifespan(object()) as state:
        assert "service" in state
        assert not client.is_closed
    assert client.is_closed


async def test_lifespan_second_close_is_safe() -> None:
    """Closing an already-closed client in the lifespan does not raise."""
    client = httpx.AsyncClient()
    await client.aclose()
    lifespan = make_server_lifespan(client)
    async with lifespan(object()):
        pass
    assert client.is_closed


def test_aclose_client_sync_closes_open_client() -> None:
    """aclose_client_sync closes a client from synchronous code."""
    client = httpx.AsyncClient()
    aclose_client_sync(client)
    assert client.is_closed
