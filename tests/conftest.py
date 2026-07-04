"""Shared test fixtures for OpenAPI MCP."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
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


@pytest.fixture
async def client() -> AsyncIterator[Client[Any]]:
    """Return an in-memory FastMCP client connected to a fresh server."""
    server = make_server()
    async with Client(server) as c:
        yield c
