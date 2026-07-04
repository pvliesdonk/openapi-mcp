"""Service lifespan + dependency injection for OpenAPI MCP.

The OpenAPI-provider lifespan owns the upstream ``httpx.AsyncClient``: it is
built in ``make_server()`` (the provider needs it at construction), threaded
into ``make_server_lifespan``, and closed here on shutdown. ``server_lifespan``
is the stock template lifespan, retained until ``server.py`` switches to the
factory in Task 8.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Any, TypedDict

import httpx
from fastmcp.dependencies import CurrentContext
from fastmcp.server.context import Context

from openapi_mcp.domain import Service

logger = logging.getLogger(__name__)


class LifespanState(TypedDict):
    """Shape of the lifespan context yielded to request handlers."""

    service: Service


@asynccontextmanager
async def server_lifespan(_mcp: object) -> AsyncIterator[dict[str, Any]]:
    """Stock template lifespan (no upstream client).

    Retained only until ``server.py`` switches to ``make_server_lifespan`` in
    Task 8, which then removes this function.
    """
    service = Service()
    await service.start()
    logger.info("Service started")
    try:
        yield {"service": service}
    finally:
        await service.stop()
        logger.info("Service stopped")


def make_server_lifespan(
    client: httpx.AsyncClient,
) -> Callable[[object], AbstractAsyncContextManager[dict[str, Any]]]:
    """Build a lifespan that owns *client*'s lifetime.

    The returned lifespan starts the health ``Service`` on entry and, on
    exit, stops it and closes the upstream client exactly once (a second
    close is a no-op).
    """

    @asynccontextmanager
    async def _lifespan(_mcp: object) -> AsyncIterator[dict[str, Any]]:
        service = Service()
        await service.start()
        logger.info("Service started")
        try:
            yield {"service": service}
        finally:
            await service.stop()
            if not client.is_closed:
                await client.aclose()
            logger.info("Service stopped; upstream client closed")

    return _lifespan


def aclose_client_sync(client: httpx.AsyncClient) -> None:
    """Close *client* from synchronous code (boot-failure cleanup).

    ``make_server()`` runs before the server's event loop, so a boot failure
    after the client is built has no running loop; ``asyncio.run`` closes the
    connection pool. If a loop is somehow already running, this is a no-op
    (best effort — the process is failing to boot regardless).
    """
    if client.is_closed:
        return
    try:
        asyncio.run(client.aclose())
    except RuntimeError:
        logger.warning("could not close upstream client synchronously")


def get_service(ctx: Context = CurrentContext()) -> Service:
    """Resolve the running :class:`Service` from the request context.

    Use as a ``Depends`` default in tool/resource/prompt handlers.

    Raises:
        RuntimeError: If the server lifespan has not run.
    """
    service: Service | None = ctx.lifespan_context.get("service")
    if service is None:
        msg = "Service not initialised — server lifespan has not run"
        raise RuntimeError(msg)
    return service
