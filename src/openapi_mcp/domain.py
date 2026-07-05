"""Domain logic for OpenAPI MCP.

Two responsibilities live here, both plain Python (no FastMCP imports) so
they unit-test without a server:

* ``Service`` — the retained fleet-standard health check.
* The OpenAPI spec/auth core — spec loading, base-URL resolution, required-
  scheme discovery, and authenticated ``httpx.AsyncClient`` construction.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
import yaml

if TYPE_CHECKING:
    from collections.abc import Callable, Generator


class BootConfigError(RuntimeError):
    """Raised for any fail-loud boot-time misconfiguration."""


@dataclass(frozen=True)
class SchemeRef:
    """A security scheme actually referenced by the spec's requirements."""

    key: str
    type: str
    location: str | None
    name: str | None
    scheme: str | None


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
        except (OSError, UnicodeDecodeError) as exc:
            # UnicodeDecodeError subclasses ValueError, not OSError — catch it
            # explicitly so a non-UTF-8 spec file fails loud as BootConfigError.
            raise BootConfigError(f"could not read spec file {value!r}: {exc}") from exc
    else:
        client = http_client or httpx.Client(timeout=30.0)
        try:
            resp = client.get(value)
            resp.raise_for_status()
            text = resp.text
        except (httpx.HTTPError, httpx.InvalidURL) as exc:
            # httpx.InvalidURL does NOT subclass httpx.HTTPError, so a malformed
            # OAPI_SPEC_URL would otherwise escape as a raw traceback instead of
            # this module's fail-loud BootConfigError.
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


def _collect_security_references(requirements: object, referenced: set[str]) -> None:
    """Extract scheme keys from a security requirements list."""
    if isinstance(requirements, list):
        for req in requirements:
            if isinstance(req, dict):
                referenced.update(req.keys())


def _collect_path_references(spec: dict[str, Any], referenced: set[str]) -> None:
    """Extract scheme keys from all path item operation security blocks."""
    for path_item in (spec.get("paths") or {}).values():
        if isinstance(path_item, dict):
            for operation in path_item.values():
                if isinstance(operation, dict):
                    _collect_security_references(operation.get("security"), referenced)


def _make_scheme_ref(key: str, defn: dict[str, Any]) -> SchemeRef:
    """Create a SchemeRef from a security scheme definition."""
    return SchemeRef(
        key=key,
        type=str(defn.get("type", "")),
        location=defn.get("in"),
        name=defn.get("name"),
        scheme=defn.get("scheme"),
    )


def required_schemes(spec: dict[str, Any]) -> list[SchemeRef]:
    """Return the schemes referenced by root/operation ``security:`` blocks.

    Only *referenced* schemes are returned; a scheme declared under
    ``components.securitySchemes`` but never required is omitted.

    Raises:
        BootConfigError: if a requirement references an undefined scheme.
    """
    definitions = (spec.get("components") or {}).get("securitySchemes") or {}
    referenced: set[str] = set()

    _collect_security_references(spec.get("security"), referenced)
    _collect_path_references(spec, referenced)

    result: list[SchemeRef] = []
    for key in sorted(referenced):
        defn = definitions.get(key)
        if not isinstance(defn, dict):
            raise BootConfigError(
                f"security requirement references undefined scheme {key!r}"
            )
        result.append(_make_scheme_ref(key, defn))
    return result


def _set_unique(mapping: dict[str, str], key: str, value: str, scheme_key: str) -> None:
    """Set ``mapping[key] = value``, failing loud if *key* is already taken.

    Raises:
        BootConfigError: if *key* was already set by another required scheme.
    """
    if key in mapping:
        raise BootConfigError(
            f"scheme {scheme_key!r} injects into {key!r}, which another "
            "required scheme already set; two schemes cannot share the same "
            "header or query key"
        )
    mapping[key] = value


def _inject_scheme(
    ref: SchemeRef,
    value: str,
    headers: dict[str, str],
    params: dict[str, str],
) -> None:
    """Inject one scheme's credential into *headers* or *params* in place.

    Raises:
        BootConfigError: on an unsupported type/location/scheme or a
            malformed ``basic`` value.
    """
    if ref.type == "apiKey":
        if ref.location == "header" and ref.name:
            _set_unique(headers, ref.name, value, ref.key)
        elif ref.location == "query" and ref.name:
            _set_unique(params, ref.name, value, ref.key)
        else:
            raise BootConfigError(
                f"apiKey scheme {ref.key!r} has unsupported location "
                f"{ref.location!r} / name {ref.name!r}"
            )
        return
    if ref.type == "http":
        scheme = (ref.scheme or "").lower()
        if scheme == "bearer":
            _set_unique(headers, "Authorization", f"Bearer {value}", ref.key)
        elif scheme == "basic":
            if ":" not in value:
                raise BootConfigError(
                    f"http basic scheme {ref.key!r} needs a 'user:pass' value"
                )
            user, _, password = value.partition(":")
            token = base64.b64encode(f"{user}:{password}".encode()).decode()
            _set_unique(headers, "Authorization", f"Basic {token}", ref.key)
        else:
            raise BootConfigError(
                f"http scheme {ref.key!r} uses unsupported scheme {ref.scheme!r} "
                "(only bearer/basic are in scope)"
            )
        return
    raise BootConfigError(
        f"scheme {ref.key!r} of type {ref.type!r} needs a dedicated server "
        "(oauth2/openIdConnect/mutualTLS are out of scope)"
    )


class _UpstreamAuth(httpx.Auth):
    """Inject static upstream credentials on every outgoing request.

    Credentials cannot ride on httpx's client-level ``headers``/``params``:
    FastMCP's ``OpenAPIProvider`` tool path builds the request with
    ``RequestDirector`` and dispatches it via ``client.send()``, which bypasses
    the client-level merge that only happens in ``build_request``. The provider
    re-copies ``client.headers`` by hand but not ``client.params``, so a
    query-scheme credential set that way silently never reaches the wire. The
    auth flow, by contrast, runs on every ``client.send()`` regardless of how
    the request was constructed, so routing both header and query schemes
    through it is the one mechanism that reliably reaches the upstream.

    Existing request headers/params win: an operation that already carries a
    key of the same name is left untouched, matching the provider's prior
    "copy header only if absent" precedence.
    """

    def __init__(self, *, headers: dict[str, str], params: dict[str, str]) -> None:
        # Copy so the "fixed credential set" invariant is owned by this type,
        # not by whatever caller passed the dicts.
        self._headers = dict(headers)
        self._params = dict(params)

    def auth_flow(
        self, request: httpx.Request
    ) -> Generator[httpx.Request, httpx.Response, None]:
        """Apply the credentials to *request*, then yield it for dispatch."""
        for key, value in self._headers.items():
            if key not in request.headers:
                request.headers[key] = value
        to_add = {
            key: value
            for key, value in self._params.items()
            if key not in request.url.params
        }
        if to_add:
            request.url = request.url.copy_merge_params(to_add)
        yield request


def build_upstream_client(
    *,
    spec: dict[str, Any],
    base_url: str,
    timeout: float,
    env_lookup: Callable[[str], str | None],
    transport: httpx.AsyncBaseTransport | None = None,
) -> httpx.AsyncClient:
    """Build an authenticated upstream client for the wrapped API.

    Credentials are injected through an :class:`_UpstreamAuth` auth flow (not
    client-level ``headers``/``params``) so they survive the request
    construction FastMCP's ``OpenAPIProvider`` performs — see that class's
    docstring for why the client-level path is unreliable.

    Raises:
        BootConfigError: on a non-positive timeout, a missing credential
            (message names the scheme key and its ``OAPI_SECURITY_*`` env var),
            or an unsupported/malformed scheme (message names the scheme key).
    """
    if timeout <= 0:
        # httpx treats timeout=0 as an instant timeout (every request fails),
        # not "disabled"; reject it loudly rather than shipping a broken client.
        raise BootConfigError(f"OAPI_HTTP_TIMEOUT must be positive; got {timeout!r}")
    headers: dict[str, str] = {}
    params: dict[str, str] = {}
    for ref in required_schemes(spec):
        value = env_lookup(ref.key)
        if not value:
            raise BootConfigError(
                f"missing upstream credential for scheme {ref.key!r}: "
                f"set OAPI_SECURITY_{ref.key.upper()}"
            )
        _inject_scheme(ref, value, headers, params)

    kwargs: dict[str, Any] = {
        "base_url": base_url,
        "timeout": timeout,
    }
    if headers or params:
        kwargs["auth"] = _UpstreamAuth(headers=headers, params=params)
    if transport is not None:
        kwargs["transport"] = transport
    return httpx.AsyncClient(**kwargs)
