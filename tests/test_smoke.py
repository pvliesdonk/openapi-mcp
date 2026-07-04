"""Smoke tests for OpenAPI MCP."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastmcp import Client

from openapi_mcp._server_apps import register_apps
from openapi_mcp.server import make_server


def test_make_server_constructs() -> None:
    """make_server() returns a FastMCP instance without raising."""
    server = make_server()
    assert server is not None


def test_register_apps_logs_when_app_domain_set(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """register_apps logs the configured app domain when the env var is set.

    Covers the ``if app_domain:`` branch of ``_server_apps.register_apps``,
    which the default smoke tests miss because no ``OAPI_APP_DOMAIN``
    is set in the test env.  Pass a real ``FastMCP`` instance so the test
    keeps working if a downstream maintainer adds real registrations to the
    branch (the scaffold's no-op branch ignores the argument today).
    """
    monkeypatch.setenv("OAPI_APP_DOMAIN", "example.com")
    with caplog.at_level("INFO", logger="openapi_mcp._server_apps"):
        register_apps(make_server())
    # Assert on the structured log argument by exact equality rather than a
    # substring test of the formatted message.  ``"example.com" in r.message``
    # trips CodeQL's ``py/incomplete-url-substring-sanitization`` rule on the
    # host-shaped literal, even though this is a log assertion and not URL
    # sanitization; ``==`` is not a substring-membership pattern, so it does
    # not.  The branch logs the configured domain as its sole ``%s`` arg.
    assert any(r.args == ("example.com",) for r in caplog.records)


async def test_status_resource_reports_ready(client: Client[Any]) -> None:
    """The example ``status://`` resource reports a started service.

    The lifespan calls ``service.start()``, so the resource payload must
    contain ``ready: true`` — asserting the value (not just the key name)
    catches a future regression where the lifespan stops starting the
    service.
    """
    result = await client.read_resource("status://openapi-mcp")
    first = result[0]
    assert hasattr(first, "text"), (
        f"expected text resource content, got {type(first).__name__}"
    )
    assert json.loads(first.text) == {"ready": True}


async def test_get_server_info_tool_registered(client: Client[Any]) -> None:
    """``get_server_info`` is wired by default and returns the wrapper info.

    The default scaffold registers the helper without an upstream provider,
    so the response carries ``server_name``, ``server_version``, and
    ``core_version`` — no ``upstream`` block. Projects that wire an
    upstream provider inside the ``DOMAIN-UPSTREAM`` sentinel in
    ``server.py`` extend this contract.
    """
    tools = {t.name for t in await client.list_tools()}
    assert "get_server_info" in tools

    result = await client.call_tool("get_server_info", {})
    first = result.content[0]
    assert hasattr(first, "text"), (
        f"expected text tool content, got {type(first).__name__}"
    )
    payload = json.loads(first.text)
    assert payload["server_name"] == "openapi-mcp"
    assert "server_version" in payload
    assert "core_version" in payload
    # No upstream block in the default scaffold — locks in the contract that
    # projects opt into by wiring the DOMAIN-UPSTREAM sentinel in server.py.
    assert "upstream" not in payload


def test_server_name_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """``OAPI_SERVER_NAME`` overrides the FastMCP server name.

    Unset, the name defaults to ``openapi-mcp`` (locked by the
    ``get_server_info`` test above). Set, ``make_server()`` must honor it so an
    operator can rename an instance without editing template-owned code.
    """
    monkeypatch.setenv("OAPI_SERVER_NAME", "renamed-instance")
    assert make_server().name == "renamed-instance"


async def test_server_name_env_override_reaches_server_info(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The overridden name also flows through to ``get_server_info``.

    ``register_server_info_tool`` is wired separately from the FastMCP ``name``,
    so this pins that both surfaces honor the same resolved name.
    """
    monkeypatch.setenv("OAPI_SERVER_NAME", "renamed-instance")
    server = make_server()
    async with Client(server) as smoke_client:
        result = await smoke_client.call_tool("get_server_info", {})
    first = result.content[0]
    assert hasattr(first, "text"), (
        f"expected text tool content, got {type(first).__name__}"
    )
    assert json.loads(first.text)["server_name"] == "renamed-instance"


def test_instructions_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """``OAPI_INSTRUCTIONS`` replaces the built-in instructions.

    ``build_instructions`` advertises this override in its hint line; honoring
    it here makes that advertisement true instead of a dead hint.
    """
    monkeypatch.setenv("OAPI_INSTRUCTIONS", "Custom operator text.")
    assert make_server().instructions == "Custom operator text."


def test_instructions_default_falls_back_to_build_instructions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unset, instructions fall back to ``build_instructions`` (whose hint
    advertises the override var). Guards the fallback arm of the override."""
    monkeypatch.delenv("OAPI_INSTRUCTIONS", raising=False)
    assert "OAPI_INSTRUCTIONS" in (make_server().instructions or "")


def test_blank_overrides_fall_back_to_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Whitespace-only overrides fall back, honoring the "unset/empty" contract.

    ``env`` strips and treats a blank value as unset, so a blank SERVER_NAME
    must revert to ``openapi-mcp`` rather than rename the instance to
    whitespace, and a blank INSTRUCTIONS must revert to ``build_instructions``.
    Guards against a future refactor (e.g. raw ``os.environ.get``) that would
    pass the blank value through.
    """
    monkeypatch.setenv("OAPI_SERVER_NAME", "   ")
    monkeypatch.setenv("OAPI_INSTRUCTIONS", "   ")
    server = make_server()
    assert server.name == "openapi-mcp"
    assert "OAPI_INSTRUCTIONS" in (server.instructions or "")


async def test_summarize_prompt_includes_context(client: Client[Any]) -> None:
    """The example ``summarize`` prompt round-trips its ``context`` argument."""
    result = await client.get_prompt("summarize", {"context": "hello world"})
    content = result.messages[0].content
    assert hasattr(content, "text"), (
        f"expected text prompt content, got {type(content).__name__}"
    )
    assert "hello world" in content.text


async def test_no_file_exchange_scaffolding(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """make_server() registers no file-exchange tools.

    The scaffold no longer calls ``register_file_exchange`` (removed
    because the upstream pvl-core 3.x line dropped the API). Under the
    HTTP + ``MCP_EXCHANGE_DIR`` configuration that previously activated
    the producer tool, ``create_download_link`` is absent — so re-adding
    ``register_file_exchange`` to ``make_server()`` would re-register it
    and fail the first assertion below. The ``fetch_file`` /
    ``create_upload_link`` assertions are defence-in-depth.
    """
    monkeypatch.setenv("OAPI_TRANSPORT", "http")
    monkeypatch.setenv("OAPI_BASE_URL", "https://test.example.com")
    monkeypatch.setenv("MCP_EXCHANGE_DIR", str(tmp_path))

    server = make_server(transport="http")
    async with Client(server) as smoke_client:
        tools = {t.name for t in await smoke_client.list_tools()}
    assert "create_download_link" not in tools
    assert "fetch_file" not in tools
    assert "create_upload_link" not in tools
