"""Configuration for OpenAPI MCP.

Composes :class:`fastmcp_pvl_core.ServerConfig` via the domain
:class:`ProjectConfig` dataclass — never inherits.

Add domain-specific fields between the CONFIG-FIELDS sentinels; copier
update preserves that block across template updates.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fastmcp_pvl_core import ConfigurationError, ServerConfig, env, env_float

_ENV_PREFIX = "OAPI"


@dataclass(frozen=True)
class ProjectConfig:
    """Domain config for OpenAPI MCP.  Compose — don't inherit."""

    server: ServerConfig = field(default_factory=ServerConfig)

    # CONFIG-FIELDS-START — add domain fields below; kept across copier update
    spec_url: str | None = None
    spec_path: str | None = None
    api_base_url: str | None = None
    http_timeout: float = 30.0
    # CONFIG-FIELDS-END

    def __post_init__(self) -> None:
        """Validate domain-field invariants on every construction path.

        Runs for ``from_env`` and direct construction alike, so a non-positive
        ``http_timeout`` fails loud at config-load. ``env_float(minimum=0.0)``
        already rejects negative env values; this also catches ``0`` (which that
        inclusive bound lets through) and a non-positive value passed directly to
        the constructor. It raises the same ``ConfigurationError`` ``env_float``
        uses, so at config-load a malformed, negative, or zero timeout all
        surface as one error type.

        ``build_upstream_client`` keeps a separate ``BootConfigError`` guard on
        the raw ``timeout`` it receives — unreachable for config-sourced values
        (already validated here) but retained for direct callers. The two layers
        own their own contract and error type by design.
        """
        if self.http_timeout <= 0:
            raise ConfigurationError(
                f"OAPI_HTTP_TIMEOUT must be positive; got {self.http_timeout!r} "
                "(0 is an instant httpx timeout, not 'disabled')"
            )

    @classmethod
    def from_env(cls) -> ProjectConfig:
        """Load :class:`ProjectConfig` from ``OAPI_*`` env vars."""
        return cls(
            server=ServerConfig.from_env(_ENV_PREFIX),
            # CONFIG-FROM-ENV-START — populate domain fields below; kept across copier update
            spec_url=env(_ENV_PREFIX, "SPEC_URL"),
            spec_path=env(_ENV_PREFIX, "SPEC_PATH"),
            api_base_url=env(_ENV_PREFIX, "API_BASE_URL"),
            http_timeout=env_float(
                _ENV_PREFIX, "HTTP_TIMEOUT", 30.0, strict=True, minimum=0.0
            ),
            # CONFIG-FROM-ENV-END
        )
