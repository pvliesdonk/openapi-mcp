"""Unit tests for the openapi_mcp spec/auth core and config."""

from __future__ import annotations

import pytest

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
