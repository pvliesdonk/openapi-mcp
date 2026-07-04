"""Integration + lifecycle tests for the OpenAPI wrapper server."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import httpx
import pytest
from fastmcp import Client

from openapi_mcp import domain
from openapi_mcp._server_deps import aclose_client_sync, make_server_lifespan
from openapi_mcp.server import make_server

if TYPE_CHECKING:
    from collections.abc import Callable


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


def _mock_upstream_build(
    handler: Callable[[httpx.Request], httpx.Response],
) -> Callable[..., httpx.AsyncClient]:
    """Return a build_upstream_client replacement that injects a MockTransport."""

    def _build(**kwargs: Any) -> httpx.AsyncClient:
        return domain.build_upstream_client(
            **kwargs, transport=httpx.MockTransport(handler)
        )

    return _build


async def test_provider_tools_listed_with_ping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The spec's operation appears as a tool alongside the retained ping."""

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"id": 1}])

    monkeypatch.setattr(
        "openapi_mcp.server.build_upstream_client", _mock_upstream_build(handler)
    )
    server = make_server()
    async with Client(server) as client:
        names = {t.name for t in await client.list_tools()}
    assert "list_things" in names
    assert "ping" in names


async def test_calling_provider_tool_injects_credential(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Calling the generated tool routes upstream with the api-key header set."""
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["x-api-key"] = request.headers.get("X-API-Key", "")
        return httpx.Response(200, json=[{"id": 1}])

    monkeypatch.setattr(
        "openapi_mcp.server.build_upstream_client", _mock_upstream_build(handler)
    )
    server = make_server()
    async with Client(server) as client:
        await client.call_tool("list_things", {})
    assert seen["x-api-key"] == "test-key"


def test_missing_spec_fails_loud(monkeypatch: pytest.MonkeyPatch) -> None:
    """Neither SPEC_URL nor SPEC_PATH set is a fail-loud boot error."""
    monkeypatch.delenv("OAPI_SPEC_PATH", raising=False)
    monkeypatch.delenv("OAPI_SPEC_URL", raising=False)
    with pytest.raises(domain.BootConfigError, match="exactly one"):
        make_server()


def test_boot_failure_after_client_build_closes_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If boot fails after the client is built, make_server closes it."""
    built: list[httpx.AsyncClient] = []
    real_build = domain.build_upstream_client

    def spy_build(**kwargs: Any) -> httpx.AsyncClient:
        client = real_build(**kwargs)
        built.append(client)
        return client

    class _Boom:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            raise RuntimeError("provider boom")

    monkeypatch.setattr("openapi_mcp.server.build_upstream_client", spy_build)
    monkeypatch.setattr("openapi_mcp.server.OpenAPIProvider", _Boom)

    with pytest.raises(RuntimeError, match="provider boom"):
        make_server()
    assert built and built[0].is_closed
