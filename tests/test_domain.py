"""Unit tests for the openapi_mcp spec/auth core and config."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

from openapi_mcp import domain
from openapi_mcp.config import ProjectConfig


def test_config_reads_spec_and_timeout_from_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ProjectConfig.from_env picks up the OAPI_* spec/base/timeout vars."""
    monkeypatch.delenv("OAPI_SPEC_PATH", raising=False)
    monkeypatch.setenv("OAPI_SPEC_URL", "https://api.example.test/openapi.json")
    monkeypatch.setenv("OAPI_API_BASE_URL", "https://api.example.test")
    monkeypatch.setenv("OAPI_HTTP_TIMEOUT", "12.5")
    cfg = ProjectConfig.from_env()
    assert cfg.spec_url == "https://api.example.test/openapi.json"
    assert cfg.spec_path is None
    assert cfg.api_base_url == "https://api.example.test"
    assert cfg.http_timeout == 12.5


def test_config_timeout_defaults_to_30(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unset OAPI_HTTP_TIMEOUT falls back to 30.0 seconds."""
    monkeypatch.delenv("OAPI_HTTP_TIMEOUT", raising=False)
    assert ProjectConfig.from_env().http_timeout == 30.0


def test_config_malformed_timeout_fails_loud(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A malformed OAPI_HTTP_TIMEOUT fails loud (strict env_float)."""
    from fastmcp_pvl_core import ConfigurationError

    monkeypatch.setenv("OAPI_HTTP_TIMEOUT", "not-a-number")
    with pytest.raises(ConfigurationError):
        ProjectConfig.from_env()


def test_config_zero_timeout_fails_loud_at_config_load(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OAPI_HTTP_TIMEOUT=0 is rejected at config-load, not just at client build.

    ``env_float(minimum=0.0)`` is inclusive so 0 slips past it; ``__post_init__``
    is what catches it. Same ``ConfigurationError`` as the negative case below,
    so the timeout field rejects every bad value with one error type.
    """
    from fastmcp_pvl_core import ConfigurationError

    monkeypatch.setenv("OAPI_HTTP_TIMEOUT", "0")
    with pytest.raises(ConfigurationError, match="OAPI_HTTP_TIMEOUT"):
        ProjectConfig.from_env()


def test_config_negative_timeout_fails_loud_at_config_load(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A negative OAPI_HTTP_TIMEOUT fails loud at config-load (env_float bound)."""
    from fastmcp_pvl_core import ConfigurationError

    monkeypatch.setenv("OAPI_HTTP_TIMEOUT", "-5")
    with pytest.raises(ConfigurationError):
        ProjectConfig.from_env()


def test_config_direct_nonpositive_timeout_fails_loud() -> None:
    """Direct ProjectConfig(http_timeout=<=0) is rejected too (bypasses from_env)."""
    from fastmcp_pvl_core import ConfigurationError

    with pytest.raises(ConfigurationError, match="OAPI_HTTP_TIMEOUT"):
        ProjectConfig(http_timeout=0.0)
    with pytest.raises(ConfigurationError, match="OAPI_HTTP_TIMEOUT"):
        ProjectConfig(http_timeout=-5.0)


def test_config_positive_timeout_constructs() -> None:
    """A positive http_timeout (and the default) constructs cleanly."""
    assert ProjectConfig(http_timeout=1.0).http_timeout == 1.0
    assert ProjectConfig().http_timeout == 30.0


def test_resolve_spec_source_exactly_one() -> None:
    assert domain.resolve_spec_source("http://x/spec.json", None) == (
        "url",
        "http://x/spec.json",
    )
    assert domain.resolve_spec_source(None, "/specs/api.yaml") == (
        "path",
        "/specs/api.yaml",
    )


def test_resolve_spec_source_rejects_both_and_neither() -> None:
    with pytest.raises(domain.BootConfigError, match="exactly one"):
        domain.resolve_spec_source("http://x", "/p")
    with pytest.raises(domain.BootConfigError, match="exactly one"):
        domain.resolve_spec_source(None, None)


def test_load_spec_from_path_json(tmp_path: Path) -> None:
    spec = {"openapi": "3.0.0", "info": {"title": "t"}, "paths": {}}
    p = tmp_path / "s.json"
    p.write_text(json.dumps(spec), encoding="utf-8")
    assert domain.load_spec(("path", str(p)))["openapi"] == "3.0.0"


def test_load_spec_from_path_yaml(tmp_path: Path) -> None:
    p = tmp_path / "s.yaml"
    p.write_text("openapi: 3.0.0\ninfo:\n  title: t\npaths: {}\n", encoding="utf-8")
    assert domain.load_spec(("path", str(p)))["info"]["title"] == "t"


def test_load_spec_missing_file_fails_loud(tmp_path: Path) -> None:
    with pytest.raises(domain.BootConfigError, match="could not read"):
        domain.load_spec(("path", str(tmp_path / "nope.json")))


def test_load_spec_non_utf8_file_fails_loud(tmp_path: Path) -> None:
    """A spec file with invalid UTF-8 bytes fails loud as BootConfigError."""
    p = tmp_path / "bad-bytes.json"
    p.write_bytes(b"\xff\xfe not valid utf-8")
    with pytest.raises(domain.BootConfigError, match="could not read spec file"):
        domain.load_spec(("path", str(p)))


def test_load_spec_unparseable_fails_loud(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text("{ this is : not : valid ]", encoding="utf-8")
    with pytest.raises(domain.BootConfigError, match="could not parse"):
        domain.load_spec(("path", str(p)))


def test_load_spec_not_openapi_doc_fails_loud(tmp_path: Path) -> None:
    p = tmp_path / "plain.json"
    p.write_text(json.dumps({"hello": "world"}), encoding="utf-8")
    with pytest.raises(domain.BootConfigError, match="not an OpenAPI"):
        domain.load_spec(("path", str(p)))


def test_load_spec_from_url_uses_injected_client() -> None:
    spec = {"openapi": "3.0.0", "info": {"title": "t"}, "paths": {}}

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://api.example.test/openapi.json"
        return httpx.Response(200, json=spec)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = domain.load_spec(
        ("url", "https://api.example.test/openapi.json"), http_client=client
    )
    assert result["openapi"] == "3.0.0"
    # An injected client is caller-owned: load_spec must not close it.
    assert not client.is_closed


def test_load_spec_url_self_client_constructs_and_closes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With no injected client, load_spec builds its own client and closes it.

    This is the branch ``make_server()`` takes for any ``OAPI_SPEC_URL``
    deployment: ``http_client is None`` -> ``httpx.Client(timeout=30.0)``,
    closed in the ``finally``.
    """
    spec = {"openapi": "3.0.0", "info": {"title": "t"}, "paths": {}}

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=spec)

    real_client_cls = httpx.Client
    created: list[httpx.Client] = []
    captured_kwargs: dict[str, object] = {}

    def fake_client(*_args: object, **kwargs: object) -> httpx.Client:
        captured_kwargs.update(kwargs)
        client = real_client_cls(transport=httpx.MockTransport(handler))
        created.append(client)
        return client

    monkeypatch.setattr("openapi_mcp.domain.httpx.Client", fake_client)
    result = domain.load_spec(("url", "https://api.example.test/openapi.json"))

    assert result["openapi"] == "3.0.0"
    assert captured_kwargs.get("timeout") == 30.0
    assert created and created[0].is_closed


def test_load_spec_url_self_client_closed_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The self-built spec-fetch client is closed even when the fetch fails.

    Guards the ``finally: if http_client is None: client.close()`` branch on the
    failure path — the URL-failure tests inject their own client, so without
    this the self-client close-on-error would be uncovered.
    """

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="nope")

    real_client_cls = httpx.Client
    created: list[httpx.Client] = []

    def fake_client(*_args: object, **_kwargs: object) -> httpx.Client:
        client = real_client_cls(transport=httpx.MockTransport(handler))
        created.append(client)
        return client

    monkeypatch.setattr("openapi_mcp.domain.httpx.Client", fake_client)
    with pytest.raises(domain.BootConfigError):
        domain.load_spec(("url", "https://api.example.test/openapi.json"))

    assert created and created[0].is_closed


def test_load_spec_url_non_2xx_fails_loud() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="nope")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(domain.BootConfigError, match=r"openapi\.json"):
        domain.load_spec(
            ("url", "https://api.example.test/openapi.json"), http_client=client
        )


def test_resolve_base_url_override_wins() -> None:
    spec = {"servers": [{"url": "https://spec.example.test"}]}
    assert (
        domain.resolve_base_url(spec, "https://override.example.test")
        == "https://override.example.test"
    )


def test_resolve_base_url_falls_back_to_spec_servers() -> None:
    spec = {"servers": [{"url": "https://spec.example.test"}]}
    assert domain.resolve_base_url(spec, None) == "https://spec.example.test"


def test_resolve_base_url_empty_servers_fails_loud() -> None:
    with pytest.raises(domain.BootConfigError, match="base URL"):
        domain.resolve_base_url({"servers": []}, None)
    with pytest.raises(domain.BootConfigError, match="base URL"):
        domain.resolve_base_url({}, None)


def test_resolve_base_url_relative_fails_loud() -> None:
    with pytest.raises(domain.BootConfigError, match="base URL"):
        domain.resolve_base_url({"servers": [{"url": "/v1"}]}, None)


def test_resolve_base_url_placeholder_fails_loud() -> None:
    with pytest.raises(domain.BootConfigError, match="base URL"):
        domain.resolve_base_url({"servers": [{"url": "https://{host}/v1"}]}, None)


def test_resolve_base_url_relative_override_fails_loud() -> None:
    with pytest.raises(domain.BootConfigError, match="base URL"):
        domain.resolve_base_url(
            {"servers": [{"url": "https://spec.example.test"}]}, "/relative"
        )


def _spec_with_schemes() -> dict[str, object]:
    return {
        "openapi": "3.0.0",
        "components": {
            "securitySchemes": {
                "ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "X-API-Key"},
                "BearerAuth": {"type": "http", "scheme": "bearer"},
                "UnusedAuth": {"type": "http", "scheme": "basic"},
            }
        },
        "security": [{"ApiKeyAuth": []}],
        "paths": {
            "/things": {"get": {"security": [{"BearerAuth": []}], "responses": {}}},
        },
    }


def test_required_schemes_returns_only_referenced() -> None:
    refs = domain.required_schemes(_spec_with_schemes())
    keys = [r.key for r in refs]
    assert keys == ["ApiKeyAuth", "BearerAuth"]  # sorted; UnusedAuth excluded


def test_required_schemes_populates_fields() -> None:
    refs = {r.key: r for r in domain.required_schemes(_spec_with_schemes())}
    assert refs["ApiKeyAuth"].type == "apiKey"
    assert refs["ApiKeyAuth"].location == "header"
    assert refs["ApiKeyAuth"].name == "X-API-Key"
    assert refs["BearerAuth"].type == "http"
    assert refs["BearerAuth"].scheme == "bearer"


def test_required_schemes_undefined_reference_fails_loud() -> None:
    spec = {"security": [{"Ghost": []}], "components": {"securitySchemes": {}}}
    with pytest.raises(domain.BootConfigError, match="Ghost"):
        domain.required_schemes(spec)


def test_required_schemes_no_security_returns_empty() -> None:
    assert domain.required_schemes({"openapi": "3.0.0", "paths": {}}) == []


def _one_scheme_spec(defn: dict[str, object], key: str = "Auth") -> dict[str, object]:
    return {
        "openapi": "3.0.0",
        "components": {"securitySchemes": {key: defn}},
        "security": [{key: []}],
        "paths": {},
    }


def _lookup(mapping: dict[str, str]) -> Callable[[str], str | None]:
    return lambda key: mapping.get(key)


async def _sent_request(
    spec: dict[str, object], creds: dict[str, str]
) -> httpx.Request:
    """Build the upstream client and return the request that reaches the wire.

    Dispatches a directly-built ``httpx.Request`` through ``client.send()`` —
    the exact path FastMCP's ``OpenAPIProvider`` tool call takes, which bypasses
    httpx's client-level ``headers``/``params`` merge. Asserting on this
    captured request (not on client construction state) is the only honest test
    that a credential actually reaches upstream.
    """
    captured: dict[str, httpx.Request] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["request"] = request
        return httpx.Response(200, json={})

    client = domain.build_upstream_client(
        spec=spec,
        base_url="https://api.example.test",
        timeout=5.0,
        env_lookup=_lookup(creds),
        transport=httpx.MockTransport(handler),
    )
    try:
        await client.send(httpx.Request("GET", "https://api.example.test/things"))
    finally:
        await client.aclose()
    return captured["request"]


async def test_build_client_apikey_header_reaches_wire() -> None:
    spec = _one_scheme_spec({"type": "apiKey", "in": "header", "name": "X-API-Key"})
    request = await _sent_request(spec, {"Auth": "secret-key"})
    assert request.headers["X-API-Key"] == "secret-key"


async def test_build_client_apikey_query_reaches_wire() -> None:
    spec = _one_scheme_spec({"type": "apiKey", "in": "query", "name": "api_key"})
    request = await _sent_request(spec, {"Auth": "qval"})
    assert request.url.params.get("api_key") == "qval"


async def test_build_client_http_bearer_reaches_wire() -> None:
    spec = _one_scheme_spec({"type": "http", "scheme": "bearer"})
    request = await _sent_request(spec, {"Auth": "tok123"})
    assert request.headers["Authorization"] == "Bearer tok123"


async def test_build_client_http_basic_reaches_wire() -> None:
    import base64

    spec = _one_scheme_spec({"type": "http", "scheme": "basic"})
    request = await _sent_request(spec, {"Auth": "alice:s3cret"})
    expected = base64.b64encode(b"alice:s3cret").decode()
    assert request.headers["Authorization"] == f"Basic {expected}"


def test_build_client_missing_credential_fails_loud() -> None:
    spec = _one_scheme_spec({"type": "apiKey", "in": "header", "name": "X-API-Key"})
    with pytest.raises(domain.BootConfigError, match="OAPI_SECURITY_AUTH"):
        domain.build_upstream_client(
            spec=spec,
            base_url="https://api.example.test",
            timeout=5.0,
            env_lookup=_lookup({}),
        )


def test_build_client_oauth2_fails_loud() -> None:
    spec = _one_scheme_spec({"type": "oauth2", "flows": {}})
    with pytest.raises(domain.BootConfigError, match="dedicated server"):
        domain.build_upstream_client(
            spec=spec,
            base_url="https://api.example.test",
            timeout=5.0,
            env_lookup=_lookup({"Auth": "x"}),
        )


def test_build_client_basic_without_colon_fails_loud() -> None:
    spec = _one_scheme_spec({"type": "http", "scheme": "basic"})
    with pytest.raises(domain.BootConfigError, match="user:pass"):
        domain.build_upstream_client(
            spec=spec,
            base_url="https://api.example.test",
            timeout=5.0,
            env_lookup=_lookup({"Auth": "no-colon"}),
        )


def _two_scheme_spec() -> dict[str, object]:
    return {
        "openapi": "3.0.0",
        "components": {
            "securitySchemes": {
                "HeaderAuth": {"type": "apiKey", "in": "header", "name": "X-API-Key"},
                "QueryAuth": {"type": "apiKey", "in": "query", "name": "api_key"},
            }
        },
        "security": [{"HeaderAuth": [], "QueryAuth": []}],
        "paths": {},
    }


async def test_build_client_multiple_schemes_accumulate() -> None:
    request = await _sent_request(
        _two_scheme_spec(), {"HeaderAuth": "hval", "QueryAuth": "qval"}
    )
    assert request.headers["X-API-Key"] == "hval"
    assert request.url.params.get("api_key") == "qval"


async def _sent_request_from(
    spec: dict[str, object], creds: dict[str, str], outgoing: httpx.Request
) -> httpx.Request:
    """Dispatch a caller-supplied *outgoing* request through the built client.

    Lets a test pre-populate the request with headers/query params so the
    ``_UpstreamAuth`` "existing request key wins" precedence can be asserted.
    """
    captured: dict[str, httpx.Request] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["request"] = request
        return httpx.Response(200, json={})

    client = domain.build_upstream_client(
        spec=spec,
        base_url="https://api.example.test",
        timeout=5.0,
        env_lookup=_lookup(creds),
        transport=httpx.MockTransport(handler),
    )
    try:
        await client.send(outgoing)
    finally:
        await client.aclose()
    return captured["request"]


async def test_build_client_injects_on_every_request() -> None:
    """The auth flow injects on repeated sends and holds no per-request state."""
    spec = _one_scheme_spec({"type": "apiKey", "in": "header", "name": "X-API-Key"})
    seen: list[str | None] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers.get("X-API-Key"))
        return httpx.Response(200, json={})

    client = domain.build_upstream_client(
        spec=spec,
        base_url="https://api.example.test",
        timeout=5.0,
        env_lookup=_lookup({"Auth": "cred"}),
        transport=httpx.MockTransport(handler),
    )
    try:
        await client.send(httpx.Request("GET", "https://api.example.test/a"))
        await client.send(httpx.Request("GET", "https://api.example.test/b"))
    finally:
        await client.aclose()
    assert seen == ["cred", "cred"]


async def test_build_client_credential_does_not_override_existing_header() -> None:
    """A header the operation already set wins over the injected credential.

    The operation header uses a different case than the scheme name to pin the
    case-insensitive precedence (``httpx.Headers`` membership), not just an
    exact-string match.
    """
    spec = _one_scheme_spec({"type": "apiKey", "in": "header", "name": "X-API-Key"})
    outgoing = httpx.Request(
        "GET", "https://api.example.test/things", headers={"x-api-key": "op-value"}
    )
    request = await _sent_request_from(spec, {"Auth": "cred"}, outgoing)
    assert request.headers.get_list("X-API-Key") == ["op-value"]


async def test_build_client_credential_does_not_override_existing_query() -> None:
    """A query param the operation already set wins over the credential."""
    spec = _one_scheme_spec({"type": "apiKey", "in": "query", "name": "api_key"})
    outgoing = httpx.Request("GET", "https://api.example.test/things?api_key=op-value")
    request = await _sent_request_from(spec, {"Auth": "cred"}, outgoing)
    assert request.url.params.get_list("api_key") == ["op-value"]


async def test_build_client_query_credential_preserves_other_params() -> None:
    """Injecting the credential keeps the operation's other query params."""
    spec = _one_scheme_spec({"type": "apiKey", "in": "query", "name": "api_key"})
    outgoing = httpx.Request("GET", "https://api.example.test/things?foo=bar")
    request = await _sent_request_from(spec, {"Auth": "qval"}, outgoing)
    assert request.url.params.get("foo") == "bar"
    assert request.url.params.get("api_key") == "qval"


async def test_build_client_no_scheme_attaches_no_auth() -> None:
    """A spec with no required schemes yields a working, auth-free client."""
    spec = {"openapi": "3.0.0", "components": {}, "security": [], "paths": {}}
    client = domain.build_upstream_client(
        spec=spec,
        base_url="https://api.example.test",
        timeout=5.0,
        env_lookup=_lookup({}),
    )
    try:
        assert client.auth is None
    finally:
        await client.aclose()


def test_build_client_scheme_collision_fails_loud() -> None:
    spec = {
        "openapi": "3.0.0",
        "components": {
            "securitySchemes": {
                "A": {"type": "apiKey", "in": "header", "name": "Authorization"},
                "B": {"type": "http", "scheme": "bearer"},
            }
        },
        "security": [{"A": [], "B": []}],
        "paths": {},
    }
    with pytest.raises(domain.BootConfigError, match="another required scheme"):
        domain.build_upstream_client(
            spec=spec,
            base_url="https://api.example.test",
            timeout=5.0,
            env_lookup=_lookup({"A": "tok", "B": "tok2"}),
        )


def test_load_spec_url_invalid_url_fails_loud() -> None:
    """A malformed OAPI_SPEC_URL fails loud (httpx.InvalidURL, not HTTPError)."""
    client = httpx.Client(
        transport=httpx.MockTransport(lambda _req: httpx.Response(200))
    )
    with pytest.raises(domain.BootConfigError, match="could not fetch spec"):
        domain.load_spec(("url", "http://\x00.example"), http_client=client)


def test_build_client_zero_timeout_fails_loud() -> None:
    """A non-positive OAPI_HTTP_TIMEOUT fails loud (0 = instant httpx timeout)."""
    spec = _one_scheme_spec({"type": "apiKey", "in": "header", "name": "X-API-Key"})
    with pytest.raises(domain.BootConfigError, match="must be positive"):
        domain.build_upstream_client(
            spec=spec,
            base_url="https://api.example.test",
            timeout=0.0,
            env_lookup=_lookup({"Auth": "k"}),
        )
