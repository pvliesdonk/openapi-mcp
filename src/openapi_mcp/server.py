"""OpenAPI MCP — FastMCP server entry point.

Composes the primitives from ``fastmcp-pvl-core`` into a
project-specific ``make_server()``.  See
https://gofastmcp.com/servers for the FastMCP server surface and
``fastmcp-pvl-core``'s README for the composable helpers used below.
"""

from __future__ import annotations

import logging
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

from fastmcp import FastMCP
from fastmcp.server.providers.openapi import OpenAPIProvider
from fastmcp_pvl_core import (
    ServerConfig,  # noqa: F401  — re-exported for downstream projects' convenience
    build_auth,
    build_event_store,  # noqa: F401  — re-exported for downstream projects' convenience
    build_instructions,
    build_kv_store,  # noqa: F401  — re-exported for downstream projects' convenience
    configure_logging_from_env,
    env,
    register_server_info_tool,
    resolve_auth_mode,
    wire_middleware_stack,
)

from openapi_mcp._server_apps import register_apps
from openapi_mcp._server_deps import aclose_client_sync, make_server_lifespan
from openapi_mcp.config import ProjectConfig
from openapi_mcp.domain import (
    build_upstream_client,
    load_spec,
    resolve_base_url,
    resolve_spec_source,
)
from openapi_mcp.prompts import register_prompts
from openapi_mcp.resources import register_resources
from openapi_mcp.tools import register_tools

logger = logging.getLogger(__name__)

_ENV_PREFIX = "OAPI"


def make_server(
    *,
    transport: str = "stdio",
    config: ProjectConfig | None = None,
) -> FastMCP:
    """Construct the OpenAPI MCP FastMCP server.

    Args:
        transport: ``"stdio"`` / ``"http"`` / ``"sse"``.  Used here for
            logging only.
        config: Optional pre-loaded config; default loads from env.

    Returns:
        A configured :class:`fastmcp.FastMCP` instance.
    """
    config = config or ProjectConfig.from_env()
    configure_logging_from_env()

    # Load + validate the spec BEFORE constructing FastMCP, so boot fails loud
    # before a half-built server exists and name/instructions can derive from
    # the spec's `info` block.
    source = resolve_spec_source(config.spec_url, config.spec_path)
    spec = load_spec(source)
    info = spec.get("info") or {}
    base_url = resolve_base_url(spec, config.api_base_url)

    # Operator overrides win; otherwise derive identity from the spec.
    server_name = env(_ENV_PREFIX, "SERVER_NAME") or info.get("title") or "openapi-mcp"
    instructions = env(_ENV_PREFIX, "INSTRUCTIONS") or build_instructions(
        read_only=False,
        env_prefix=_ENV_PREFIX,
        domain_line=info.get("description")
        or "A generic MCP server built at runtime from an OpenAPI spec.",
    )

    def _security_lookup(scheme_key: str) -> str | None:
        return env(_ENV_PREFIX, f"SECURITY_{scheme_key.upper()}")

    auth = build_auth(config.server)
    auth_mode = resolve_auth_mode(config.server) if auth is not None else "none"
    if auth_mode == "none":
        logger.warning(
            "No auth configured — server accepts unauthenticated connections"
        )
    else:
        logger.info("Auth enabled: mode=%s", auth_mode)

    try:
        pkg_ver = _pkg_version("pvliesdonk-openapi-mcp")
    except PackageNotFoundError:
        pkg_ver = "unknown"

    logger.info(
        "Server config: version=%s name=%s transport=%s auth=%s",
        pkg_ver,
        server_name,
        transport,
        auth_mode,
    )

    client = build_upstream_client(
        spec=spec,
        base_url=base_url,
        timeout=config.http_timeout,
        env_lookup=_security_lookup,
    )
    try:
        mcp = FastMCP(
            name=server_name,
            instructions=instructions,
            lifespan=make_server_lifespan(client),
            auth=auth,
            providers=[OpenAPIProvider(openapi_spec=spec, client=client)],
        )

        wire_middleware_stack(mcp)

        register_tools(mcp)
        register_resources(mcp)
        register_prompts(mcp)
        register_apps(mcp)

        register_server_info_tool(
            mcp,
            server_name=server_name,
            server_version=pkg_ver,
            # DOMAIN-UPSTREAM-START
            # DOMAIN-UPSTREAM-END
        )

        # DOMAIN-WIRING-START — project-specific wiring; kept across copier update.
        # DOMAIN-WIRING-END
    except BaseException:
        # Client built but boot failed before the lifespan took ownership:
        # close it here so no socket leaks on a failed boot.
        aclose_client_sync(client)
        raise

    return mcp
