# OpenAPI MCP

<!-- mcp-name: io.github.pvliesdonk/openapi-mcp -->

[![CI](https://github.com/pvliesdonk/openapi-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/pvliesdonk/openapi-mcp/actions/workflows/ci.yml) [![codecov](https://codecov.io/gh/pvliesdonk/openapi-mcp/graph/badge.svg)](https://codecov.io/gh/pvliesdonk/openapi-mcp) [![PyPI](https://img.shields.io/pypi/v/pvliesdonk-openapi-mcp)](https://pypi.org/project/pvliesdonk-openapi-mcp/) [![Python](https://img.shields.io/pypi/pyversions/pvliesdonk-openapi-mcp)](https://pypi.org/project/pvliesdonk-openapi-mcp/) [![License](https://img.shields.io/github/license/pvliesdonk/openapi-mcp)](LICENSE) [![Docker](https://img.shields.io/github/v/release/pvliesdonk/openapi-mcp?label=ghcr.io&logo=docker)](https://github.com/pvliesdonk/openapi-mcp/pkgs/container/openapi-mcp) [![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://pvliesdonk.github.io/openapi-mcp/) [![llms.txt](https://img.shields.io/badge/llms.txt-available-brightgreen)](https://pvliesdonk.github.io/openapi-mcp/llms.txt) [![Template](https://img.shields.io/badge/dynamic/yaml?url=https://raw.githubusercontent.com/pvliesdonk/openapi-mcp/main/.copier-answers.yml&query=%24._commit&label=template)](https://github.com/pvliesdonk/fastmcp-server-template)

A generic MCP server that builds its tools at runtime from any OpenAPI specification.

**[Documentation](https://pvliesdonk.github.io/openapi-mcp/)** | **[Config wizard](https://pvliesdonk.github.io/openapi-mcp/latest/configuration-generator/)** | **[PyPI](https://pypi.org/project/pvliesdonk-openapi-mcp/)** | **[Docker](https://github.com/pvliesdonk/openapi-mcp/pkgs/container/openapi-mcp)**

## Features

<!-- DOMAIN-START -->
<!-- Replace with 3-7 bullets describing what this MCP server does. Kept across copier update. -->

- **[Capability 1]:** one-sentence description of a user-visible feature.
- **[Capability 2]:** one-sentence description of another capability.
- **MCP tools:** N LLM-visible tools exposed; see `src/openapi_mcp/tools.py`.
- **MCP resources:** M resources exposing domain state; see `src/openapi_mcp/resources.py`.
- **MCP prompts:** K prompt templates; see `src/openapi_mcp/prompts.py`.
<!-- DOMAIN-END -->

## What you can do with it

<!-- DOMAIN-START -->
<!-- Replace with 3-5 concrete "you can ask Claude to X" examples. Kept across copier update. -->

With this server mounted in an MCP client (Claude, etc.), you can:

- **[Task 1]:** "[example user request]." Composes tools `[tool_a]` + `[tool_b]`.
- **[Task 2]:** "[another example request]." Uses resource `[resource_x]`.
- **[Task 3]:** "[third example]."

Short, concrete prompts beat abstract feature lists. Replace the
`[Task N]` placeholders with prompts that actually work against your
server's tool surface.
<!-- DOMAIN-END -->

<!-- ===== TEMPLATE-OWNED SECTIONS BELOW — DO NOT EDIT; CHANGES WILL BE OVERWRITTEN ON COPIER UPDATE ===== -->

## Installation

### From PyPI

```bash
pip install pvliesdonk-openapi-mcp
```

If you add optional extras via the `PROJECT-EXTRAS-START` / `PROJECT-EXTRAS-END` sentinels in `pyproject.toml`, document them below:

<!-- DOMAIN-START -->
<!-- List optional extras and their purpose here (e.g. `pip install pvliesdonk-openapi-mcp[embeddings]`). Kept across copier update. -->
<!-- DOMAIN-END -->

### From source

```bash
git clone https://github.com/pvliesdonk/openapi-mcp.git
cd openapi-mcp
uv sync --all-extras --all-groups
```

### Docker

```bash
docker pull ghcr.io/pvliesdonk/openapi-mcp:latest
```

A `compose.yml` ships at the repo root as a starting point. Copy `.env.example` to `.env`, edit, and `docker compose up -d`.

To attach a remote Python debugger (development only; the protocol is unauthenticated), see [Remote debugging](docs/deployment/docker.md#remote-debugging).

### Linux packages (.deb / .rpm)

Download `.deb` or `.rpm` packages from the [GitHub Releases](https://github.com/pvliesdonk/openapi-mcp/releases) page. Both install a hardened systemd unit; env configuration is sourced from `/etc/openapi-mcp/env` (copy from the shipped `/etc/openapi-mcp/env.example`).

### Claude Desktop (.mcpb bundle)

Download the `.mcpb` bundle from the [GitHub Releases](https://github.com/pvliesdonk/openapi-mcp/releases) page and double-click to install, or run:

```bash
mcpb install openapi-mcp-<version>.mcpb
```

Claude Desktop prompts for required env vars via a GUI wizard, with no manual JSON editing needed.

For manual Claude Desktop configuration and setup options, see [Claude Desktop deployment](docs/deployment/claude-desktop.md).

## Quick start

```bash
openapi-mcp serve                                # stdio transport
openapi-mcp serve --transport http --port 8000   # streamable HTTP
```

For library usage (embedding the domain logic without the MCP transport), import from the `openapi_mcp` package directly. See the project's domain modules under `src/openapi_mcp/` for entry points.

### Server info

The server registers a built-in `get_server_info` tool (via `fastmcp_pvl_core.register_server_info_tool`) so operators can confirm the deployed version with a single MCP call. The default response carries `server_name`, `server_version`, and `core_version`. Servers that talk to a remote upstream wire upstream version reporting inside the `DOMAIN-UPSTREAM-START` / `DOMAIN-UPSTREAM-END` sentinel in `src/openapi_mcp/server.py`; see [`CLAUDE.md`](CLAUDE.md#server-info-tool-get_server_info) for the wiring pattern.

## Configuration

Core environment variables shared across all `fastmcp-pvl-core`-based services:

| Variable | Default | Description |
|---|---|---|
| `FASTMCP_LOG_LEVEL` | `INFO` | Log level for FastMCP internals and app loggers (`DEBUG` / `INFO` / `WARNING` / `ERROR`). The `-v` CLI flag overrides to `DEBUG`. |
| `FASTMCP_ENABLE_RICH_LOGGING` | `true` | Set to `false` for plain / structured JSON log output. |
| `OAPI_KV_STORE_URL` | `file:///data/state` | Persistent-state backend URL for pvl-core subsystems: `file:///path` (survives restarts), `memory://` (dev/ephemeral). |

Domain-specific variables go below under [Domain configuration](#domain-configuration).

## Authentication

Callers authenticate via a bearer token or OIDC (mutually exclusive). See the [Authentication guide](docs/guides/authentication.md) for setup, mapped multi-subject tokens, OIDC, and troubleshooting.

## Post-scaffold checklist

After `copier copy` and `gh repo create --push`:

1. **Fill in the DOMAIN blocks** (every section marked with a `DOMAIN` sentinel comment) in this README and in `CLAUDE.md`.
2. Configure GitHub secrets (see below).
3. Install dev + docs tooling: `uv sync --all-extras --all-groups`.
4. Install pre-commit hooks: `uv run pre-commit install`.
5. Run the gate locally: `uv run pytest -x -q && uv run ruff check --fix . && uv run ruff format . && uv run mypy src/ tests/`.
6. Push the first commit. CI should be green.

## GitHub secrets

CI workflows reference three repository secrets. Configure them via **Settings → Secrets and variables → Actions** or with `gh secret set`:

| Secret | Used by | How to generate |
|---|---|---|
| `RELEASE_TOKEN` | `release.yml`, `copier-update.yml` | Fine-grained PAT at <https://github.com/settings/personal-access-tokens/new> with `contents: write` and `pull_requests: write` (the `copier-update` cron opens PRs). Scoped to this repo. |
| `CODECOV_TOKEN` | `ci.yml` | <https://codecov.io>: sign in with GitHub, add the repo, copy the upload token from the repo settings page. |
| `CLAUDE_CODE_OAUTH_TOKEN` | `claude.yml`, `claude-code-review.yml` | Run `claude setup-token` locally and paste the result. |

```bash
gh secret set RELEASE_TOKEN
gh secret set CODECOV_TOKEN
gh secret set CLAUDE_CODE_OAUTH_TOKEN
```

`GITHUB_TOKEN` is auto-provided; no action needed.

## Local development

The PR gate (matches CI):

```bash
uv run pytest -x -q                                  # tests
uv run ruff check --fix . && uv run ruff format .    # lint + format
uv run mypy src/ tests/                              # type-check
```

Pre-commit runs a subset of the gate on each commit; see `.pre-commit-config.yaml` for details, or [`CLAUDE.md`](CLAUDE.md) for the full Hard PR Acceptance Gates.

## Troubleshooting

### Moving a scaffolded project

`uv sync` creates `.venv/bin/*` scripts with absolute shebangs pointing at the venv Python. If you move the repo after scaffolding (`mv /old/path /new/path`), `uv run pytest` fails with `ModuleNotFoundError: No module named 'fastmcp'` because the stale shebang resolves to a different interpreter than the venv's site-packages.

**Fix:**

```bash
rm -rf .venv
uv sync --all-extras --all-groups
```

`uv run python -m pytest` also works as a one-shot workaround (bypasses the stale entry-script shim).

### `uv.lock` refresh after `copier update`

When `copier update` introduces new dependencies (such as a new extra added to `pyproject.toml.jinja`), CI runs `uv sync --frozen` which fails against a stale lockfile. Run `uv lock` locally and commit the refreshed `uv.lock` alongside accepting the copier-update PR.

## Links

- [Documentation](https://pvliesdonk.github.io/openapi-mcp/)
- [llms.txt](https://pvliesdonk.github.io/openapi-mcp/llms.txt)
- [FastMCP](https://gofastmcp.com)
- [fastmcp-pvl-core](https://pypi.org/project/fastmcp-pvl-core/)

<!-- ===== TEMPLATE-OWNED SECTIONS END ===== -->

## Domain configuration

<!-- DOMAIN-START -->
<!-- Replace with a table of domain-specific env vars. Kept across copier update. -->

Domain environment variables use the `OAPI_` prefix:

| Variable | Default | Required | Description |
|---|---|---|---|
| `OAPI_EXAMPLE_VAR` | (none) | **Yes** | Replace this row with your first required setting. |
| `OAPI_ANOTHER_VAR` | `default` | No | Replace with an optional setting. |

Domain-config fields are composed inside `src/openapi_mcp/config.py` between the `CONFIG-FIELDS-START` / `CONFIG-FIELDS-END` sentinels; env reads go through `fastmcp_pvl_core.env(_ENV_PREFIX, "SUFFIX", default)` so naming stays consistent.
<!-- DOMAIN-END -->

## Key design decisions

<!-- DOMAIN-START -->
<!-- Replace with 3-6 bullets describing non-obvious architectural decisions. Kept across copier update. -->

_Replace this placeholder with a short list of the non-obvious design calls this service makes, such as "writes are append-only," "embeddings cached in SQLite," or "auth uses OIDC bearer tokens." Three to six bullets is typically enough; link out to longer ADRs under `docs/decisions/` if you maintain any._
<!-- DOMAIN-END -->
