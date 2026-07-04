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
