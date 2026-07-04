"""Shared test fixtures for OpenAPI MCP."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from fastmcp import Client

from openapi_mcp.server import make_server


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip all ``OAPI_*`` env vars before each test."""
    for key in list(os.environ):
        if key.startswith("OAPI_"):
            monkeypatch.delenv(key, raising=False)


_FIXTURE_SPEC = Path(__file__).parent / "fixtures" / "petstore-min.json"


@pytest.fixture(autouse=True)
def _default_spec_env(monkeypatch: pytest.MonkeyPatch, _clear_env: None) -> None:
    """Point every ``make_server()`` at the fixture spec + a fixture key.

    ``make_server()`` now requires a spec and its referenced credential, so
    the whole suite (smoke tests included) needs a valid default. The fixture
    spec's ``info.title`` is ``openapi-mcp`` so name-derivation matches the
    existing smoke-test assertions.
    """
    monkeypatch.setenv("OAPI_SPEC_PATH", str(_FIXTURE_SPEC))
    monkeypatch.setenv("OAPI_SECURITY_APIKEYAUTH", "test-key")


@pytest.fixture
async def client() -> AsyncIterator[Client[Any]]:
    """Return an in-memory FastMCP client connected to a fresh server."""
    server = make_server()
    async with Client(server) as c:
        yield c
