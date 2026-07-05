"""Regression coverage for a real OpenAPI 3.1 header-auth fixture."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
from fastmcp import Client

from openapi_mcp import domain
from openapi_mcp.server import make_server

if TYPE_CHECKING:
    from collections.abc import Callable


FIXTURE = Path(__file__).parent / "fixtures" / "xquik-read-api.json"


def _mock_upstream_build(
    handler: Callable[[httpx.Request], httpx.Response],
) -> Callable[..., httpx.AsyncClient]:
    def _build(**kwargs: Any) -> httpx.AsyncClient:
        return domain.build_upstream_client(
            **kwargs, transport=httpx.MockTransport(handler)
        )

    return _build


async def test_xquik_fixture_exposes_read_operations(
    monkeypatch,
) -> None:
    """The Xquik OpenAPI 3.1 fixture exposes both read operations as tools."""
    monkeypatch.setenv("OAPI_SPEC_PATH", str(FIXTURE))
    monkeypatch.setenv("OAPI_SECURITY_XAPIKEY", "test-key")

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    monkeypatch.setattr(
        "openapi_mcp.server.build_upstream_client", _mock_upstream_build(handler)
    )
    server = make_server()

    async with Client(server) as client:
        names = {tool.name for tool in await client.list_tools()}

    assert {"searchTweets", "getUser", "ping"} <= names


async def test_xquik_fixture_injects_header_auth_and_path_parameter(
    monkeypatch,
) -> None:
    """Calling a path-param tool sends the configured Xquik API-key header."""
    monkeypatch.setenv("OAPI_SPEC_PATH", str(FIXTURE))
    monkeypatch.setenv("OAPI_SECURITY_XAPIKEY", "test-key")
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["key"] = request.headers.get("x-api-key", "")
        return httpx.Response(200, json={"id": "xquik"})

    monkeypatch.setattr(
        "openapi_mcp.server.build_upstream_client", _mock_upstream_build(handler)
    )
    server = make_server()

    async with Client(server) as client:
        await client.call_tool("getUser", {"id": "xquik"})

    assert seen == {"path": "/api/v1/x/users/xquik", "key": "test-key"}
