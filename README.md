# OpenAPI MCP

<!-- mcp-name: io.github.pvliesdonk/openapi-mcp -->

[![CI](https://github.com/pvliesdonk/openapi-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/pvliesdonk/openapi-mcp/actions/workflows/ci.yml) [![codecov](https://codecov.io/gh/pvliesdonk/openapi-mcp/graph/badge.svg)](https://codecov.io/gh/pvliesdonk/openapi-mcp) [![PyPI](https://img.shields.io/pypi/v/pvliesdonk-openapi-mcp)](https://pypi.org/project/pvliesdonk-openapi-mcp/) [![Python](https://img.shields.io/pypi/pyversions/pvliesdonk-openapi-mcp)](https://pypi.org/project/pvliesdonk-openapi-mcp/) [![License](https://img.shields.io/github/license/pvliesdonk/openapi-mcp)](LICENSE) [![Docker](https://img.shields.io/github/v/release/pvliesdonk/openapi-mcp?label=ghcr.io&logo=docker)](https://github.com/pvliesdonk/openapi-mcp/pkgs/container/openapi-mcp) [![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://pvliesdonk.github.io/openapi-mcp/) [![llms.txt](https://img.shields.io/badge/llms.txt-available-brightgreen)](https://pvliesdonk.github.io/openapi-mcp/llms.txt) [![Template](https://img.shields.io/badge/dynamic/yaml?url=https://raw.githubusercontent.com/pvliesdonk/openapi-mcp/main/.copier-answers.yml&query=%24._commit&label=template)](https://github.com/pvliesdonk/fastmcp-server-template)

A generic MCP server that builds its tools at runtime from any OpenAPI specification.

**[Documentation](https://pvliesdonk.github.io/openapi-mcp/)** | **[Config wizard](https://pvliesdonk.github.io/openapi-mcp/latest/configuration-generator/)** | **[PyPI](https://pypi.org/project/pvliesdonk-openapi-mcp/)** | **[Docker](https://github.com/pvliesdonk/openapi-mcp/pkgs/container/openapi-mcp)**

## Features

<!-- DOMAIN-START -->
`openapi-mcp` builds its MCP tools at runtime from any OpenAPI specification,
with no per-API code. Point one container image at a spec (URL or mounted file)
plus upstream credentials, and it exposes the operations of that API as MCP
tools via FastMCP's `OpenAPIProvider`.

Intended for **simple** APIs. Large or complex APIs, or ones using
`oauth2`/`openIdConnect`/`mutualTLS` upstream auth, are better served by a
purpose-built sibling. See
[`docs/superpowers/specs/2026-07-04-openapi-generic-wrapper-design.md`](docs/superpowers/specs/2026-07-04-openapi-generic-wrapper-design.md)
for the design and [`.env.example`](.env.example) for the full `OAPI_*` contract.

```bash
docker run --rm \
  -e OAPI_SPEC_URL=https://api.example.com/openapi.json \
  -e OAPI_SECURITY_APIKEYAUTH=your-key \
  ghcr.io/pvliesdonk/openapi-mcp
```
<!-- DOMAIN-END -->

## What you can do with it

<!-- DOMAIN-START -->
The tool surface is whatever the mounted OpenAPI spec defines: each operation
in the spec becomes one MCP tool, named by its `operationId`. The concrete
prompts depend on the API you wrap. With a spec mounted, you can ask Claude to:

- **Call an operation directly:** "List the open orders" runs the spec's
  `list_orders` operation and returns the response.
- **Chain operations:** "Find the customer named Acme, then show their most
  recent invoice" composes a search operation with a lookup operation.
- **Confirm the deployment:** "Which server version is running?" calls the
  built-in `get_server_info` tool.

Because tools are generated from the spec, the exact tool names and working
prompts match your API. Point the server at a different spec and the tool
surface changes with no code edits.
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
Domain environment variables use the `OAPI_` prefix. `openapi-mcp` derives its
tools from an OpenAPI spec at boot, so configure the spec source, upstream base
URL, timeout, and per-scheme upstream credentials. See
[`.env.example`](.env.example) for a copy-paste template and the
[configuration guide](https://pvliesdonk.github.io/openapi-mcp/latest/configuration/)
for the full contract.

| Variable | Default | Required | Description |
|---|---|---|---|
| `OAPI_SPEC_URL` | (none) | Exactly one of URL/PATH | URL of the OpenAPI spec, fetched at boot. |
| `OAPI_SPEC_PATH` | (none) | Exactly one of URL/PATH | Local or mounted spec file (JSON or YAML). |
| `OAPI_API_BASE_URL` | spec `servers[0].url` | No | Override the upstream base URL. |
| `OAPI_HTTP_TIMEOUT` | `30` | No | Upstream request timeout in seconds. |
| `OAPI_SECURITY_<SCHEMEKEY>` | (none) | If the scheme is referenced | Credential for a referenced security scheme, named by its uppercased key. |

Setting both `OAPI_SPEC_URL` and `OAPI_SPEC_PATH`, or neither, is a fail-loud
boot error. Upstream credentials cover `apiKey` (header or query), `http`
`bearer`, and `http` `basic` (a `user:pass` value); `oauth2`, `openIdConnect`,
and `mutualTLS` are out of scope and belong in a purpose-built sibling.

Domain-config fields are composed inside `src/openapi_mcp/config.py` between the `CONFIG-FIELDS-START` / `CONFIG-FIELDS-END` sentinels; env reads go through `fastmcp_pvl_core.env(_ENV_PREFIX, "SUFFIX", default)` so naming stays consistent.
<!-- DOMAIN-END -->

## Key design decisions

<!-- DOMAIN-START -->
- **Tools are derived from the spec at runtime.** Each spec operation becomes
  one MCP tool through FastMCP's `OpenAPIProvider`, so pointing the server at a
  different spec changes the tool surface with no code edits.
- **Two auth layers stay strictly separate.** Inbound auth (who may call this
  server, inherited from `fastmcp-pvl-core`) and upstream auth
  (`OAPI_SECURITY_*`, how this server authenticates to the wrapped API) never
  mix.
- **Upstream credentials ride an `httpx.Auth` flow.** They are injected when the
  request is dispatched rather than as client-level headers or query
  parameters, so they survive the request construction `OpenAPIProvider`
  performs and reach the wire for both header and query schemes.
- **Boot fails loud.** A missing or malformed spec, an ambiguous spec source,
  a missing credential, or a non-positive timeout raises at startup instead of
  surfacing as a per-request error later.
- **Scope is deliberately narrow.** Only `apiKey`, `http bearer`, and
  `http basic` upstream schemes are supported, and a credential is required for
  every referenced scheme (no "scheme A or B" alternatives). Larger or complex
  APIs, `oauth2`/`openIdConnect`/`mutualTLS` auth, and mutually exclusive auth
  alternatives belong in a purpose-built sibling.

See
[`docs/superpowers/specs/2026-07-04-openapi-generic-wrapper-design.md`](docs/superpowers/specs/2026-07-04-openapi-generic-wrapper-design.md)
for the full design rationale.
<!-- DOMAIN-END -->
