"""Configuration for OpenAPI MCP.

Composes :class:`fastmcp_pvl_core.ServerConfig` via the domain
:class:`ProjectConfig` dataclass — never inherits.

Add domain-specific fields between the CONFIG-FIELDS sentinels; copier
update preserves that block across template updates.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fastmcp_pvl_core import (
    ServerConfig,
    env,  # noqa: F401  — re-exported so CONFIG-FROM-ENV additions don't need a new import
)

_ENV_PREFIX = "OAPI"


@dataclass(frozen=True)
class ProjectConfig:
    """Domain config for OpenAPI MCP.  Compose — don't inherit."""

    server: ServerConfig = field(default_factory=ServerConfig)

    # CONFIG-FIELDS-START — add domain fields below; kept across copier update
    # (uncommenting the Path-typed examples below also requires adding
    #  ``from pathlib import Path`` to the imports at the top of this file.)
    # (example)
    # vault_path: Path = Path("/data/vault")
    # CONFIG-FIELDS-END

    @classmethod
    def from_env(cls) -> ProjectConfig:
        """Load :class:`ProjectConfig` from ``OAPI_*`` env vars."""
        return cls(
            server=ServerConfig.from_env(_ENV_PREFIX),
            # CONFIG-FROM-ENV-START — populate domain fields below; kept across copier update
            # (example)
            # vault_path=Path(env(_ENV_PREFIX, "VAULT_PATH", "/data/vault")),
            # CONFIG-FROM-ENV-END
        )
