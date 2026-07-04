"""Domain logic for OpenAPI MCP.

Two responsibilities live here, both plain Python (no FastMCP imports) so
they unit-test without a server:

* ``Service`` — the retained fleet-standard health check.
* The OpenAPI spec/auth core — spec loading, base-URL resolution, required-
  scheme discovery, and authenticated ``httpx.AsyncClient`` construction.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import yaml


class BootConfigError(RuntimeError):
    """Raised for any fail-loud boot-time misconfiguration."""


class Service:
    """Placeholder service.  Replace with real domain logic."""

    def __init__(self) -> None:
        self._ready = False

    async def start(self) -> None:
        """Start the service (connect to DB, warm caches, etc.)."""
        self._ready = True

    async def stop(self) -> None:
        """Stop the service (close connections, flush state, etc.)."""
        self._ready = False

    async def ping(self) -> str:
        """Health check."""
        return "pong" if self._ready else "not ready"

    async def status(self) -> dict[str, object]:
        """Structured status payload."""
        return {"ready": self._ready}


def resolve_spec_source(spec_url: str | None, spec_path: str | None) -> tuple[str, str]:
    """Return ``("url", value)`` or ``("path", value)``.

    Raises:
        BootConfigError: unless exactly one of the two is set.
    """
    if spec_url and not spec_path:
        return ("url", spec_url)
    if spec_path and not spec_url:
        return ("path", spec_path)
    raise BootConfigError(
        "set exactly one of OAPI_SPEC_URL or OAPI_SPEC_PATH "
        f"(url={'set' if spec_url else 'unset'}, "
        f"path={'set' if spec_path else 'unset'})"
    )


def _parse_spec_text(text: str) -> Any:
    """Parse *text* as YAML (a superset of JSON).

    Raises:
        BootConfigError: on a parse failure.
    """
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise BootConfigError(f"could not parse spec as JSON or YAML: {exc}") from exc


def load_spec(
    source: tuple[str, str], *, http_client: httpx.Client | None = None
) -> dict[str, Any]:
    """Fetch/read and parse the OpenAPI spec.

    Raises:
        BootConfigError: on read/fetch failure, parse failure, or a body
            that parses but is not an OpenAPI document.
    """
    kind, value = source
    if kind == "path":
        try:
            text = Path(value).read_text(encoding="utf-8")
        except OSError as exc:
            raise BootConfigError(f"could not read spec file {value!r}: {exc}") from exc
    else:
        client = http_client or httpx.Client(timeout=30.0)
        try:
            resp = client.get(value)
            resp.raise_for_status()
            text = resp.text
        except httpx.HTTPError as exc:
            raise BootConfigError(
                f"could not fetch spec from {value!r}: {exc}"
            ) from exc
        finally:
            if http_client is None:
                client.close()

    data = _parse_spec_text(text)
    if not isinstance(data, dict) or not (data.get("openapi") or data.get("swagger")):
        raise BootConfigError(
            f"spec body parsed but is not an OpenAPI document "
            f"(missing top-level 'openapi'/'swagger' key): got {type(data).__name__}"
        )
    return data


def resolve_base_url(spec: dict[str, Any], override: str | None) -> str:
    """Resolve the upstream base URL: override wins, else spec servers[0].

    Raises:
        BootConfigError: when no usable absolute http(s) URL is available.
    """
    if override:
        url = override
    else:
        servers = spec.get("servers")
        if not isinstance(servers, list) or not servers:
            raise BootConfigError(
                "no usable base URL: spec has no servers[] and "
                "OAPI_API_BASE_URL is unset"
            )
        first = servers[0] if isinstance(servers[0], dict) else {}
        url = str(first.get("url", ""))
    if not url or "{" in url or not url.lower().startswith(("http://", "https://")):
        raise BootConfigError(
            f"no usable base URL: {url!r} is not an absolute http(s) URL "
            "(set OAPI_API_BASE_URL to override)"
        )
    return url
