"""Unit tests for the openapi_mcp spec/auth core and config."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from openapi_mcp import domain
from openapi_mcp.config import ProjectConfig


def test_config_reads_spec_and_timeout_from_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ProjectConfig.from_env picks up the OAPI_* spec/base/timeout vars."""
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
