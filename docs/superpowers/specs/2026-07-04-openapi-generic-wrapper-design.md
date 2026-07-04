# Generic OpenAPI-wrapper MCP server — design

**Date:** 2026-07-04
**Status:** Approved (brainstorm) — awaiting spec review before planning
**Scope:** A new fleet sibling: a single, generic MCP server whose
domain tools are derived at runtime from an OpenAPI specification
supplied by env, rather than hand-written.

> This is the design for **this repository** (`openapi-mcp`). It was
> brainstormed from the `fastmcp-server-template` repo and moved here.
> The repo currently holds only the license and this design; the sibling
> is scaffolded from `fastmcp-server-template` as the first
> implementation step.

## Problem

Several fleet siblings do nothing but wrap a REST API: they hand-write a
thin `Service` client and one MCP tool per endpoint. For a *simple*
OpenAPI, that hand-work is more effort than it's worth. FastMCP already
converts an OpenAPI spec into MCP tools natively
(`fastmcp.server.providers.openapi.OpenAPIProvider`, v3 provider-based
API). We want a single container image that, given only an OpenAPI spec
(URL or mounted file) plus upstream credentials, boots a working MCP
server for that API — with no code changes and no per-API repo.

Large/complex APIs are explicitly **out of scope**: FastMCP's own docs
warn that auto-converted servers underperform curated ones, and a
purpose-built sibling (scaffolded from the template) is cheap to produce.
This server is for the simple case where a dedicated repo isn't worth it.

## Product shape

**One generic image, runtime-configured.** A single sibling repo
produces one published Docker image. Operators point it at a different
API per container via env. Same image, N deployments.

It is a **normal fleet member**: scaffolded once from
`fastmcp-server-template`, so it inherits `fastmcp-pvl-core`, inbound
auth, CI, Docker, packaging, and config **verbatim**, and it receives
copier updates like every other sibling. The *only* departure from a
stock generated project: the domain layer is derived from the spec
instead of hand-written.

## Architecture & fleet placement

The template's `make_server()` composition is preserved. The single
change is what sources the domain tools:

- `domain.py` and `tools.py` no longer hand-write domain logic.
- At `make_server()` time we **fetch + validate the spec**, **build an
  upstream `httpx.AsyncClient`**, and attach
  `OpenAPIProvider(spec, client)` via the `providers=[...]` kwarg of the
  `FastMCP(...)` constructor (documented v3 pattern:
  `FastMCP(name, providers=[OpenAPIProvider(spec, client)])`).
- `register_tools`/`register_resources`/`register_prompts`/
  `register_apps` remain. The health `ping` tool stays as the
  fleet-standard liveness check; the OpenAPI provider's tools are
  sourced alongside it.

### Two independent auth layers (kept strictly separate)

- **Inbound auth** — who may call *this MCP server*. 100% inherited from
  pvl-core `ServerConfig` / `build_auth` (bearer/OIDC). Untouched.
- **Upstream auth** — how *this server* authenticates to the wrapped
  API. The new `<PREFIX>_SECURITY_*` fields below. Never conflated with
  inbound auth.

## Config / env contract

All fields live in the template's existing `ProjectConfig` (frozen
dataclass, `CONFIG-FIELDS` sentinels) and load via
`ProjectConfig.from_env()` with the pvl-core `<PREFIX>_` convention — no
new config machinery. `<PREFIX>` is a copier var chosen at scaffold
(`OAPI` in examples below).

| Env var | Purpose | Default / fallback |
|---|---|---|
| `OAPI_SPEC_URL` | HTTPS URL of the OpenAPI spec, fetched at boot | — (exactly one of URL/PATH) |
| `OAPI_SPEC_PATH` | Local/mounted spec file, alternative to URL | — (exactly one of URL/PATH) |
| `OAPI_API_BASE_URL` | Upstream base URL override | spec `servers[0].url` |
| `OAPI_SECURITY_<SCHEMEKEY>` | Credential value per declared scheme; interpreted by scheme type | — (fail loud if a required scheme is unset) |
| `OAPI_HTTP_TIMEOUT` | Upstream request timeout (seconds) | `30` |
| `OAPI_SERVER_NAME` *(already in template)* | Rename instance | spec `info.title` |
| `OAPI_INSTRUCTIONS` *(already in template)* | Override instructions text | built from spec `info.description` |

### Domain knowledge derived from the spec

Where siblings hardcode domain identity, this server derives it:

| Domain knowledge | Siblings hardcode as | Here, derived from |
|---|---|---|
| Server name | `project_name` | spec `info.title` |
| Instructions / domain line | `domain_description` | spec `info.description` |
| Upstream base URL | a config field | spec `servers[0].url` (env override) |
| Tools | hand-written in `tools.py` | every path/operation |

### Spec source

**URL + mounted file.** `OAPI_SPEC_URL` (fetched at boot) is the primary
path; `OAPI_SPEC_PATH` serves a spec mounted into the container
(private/air-gapped APIs, k8s configmap). **Exactly one** must be set;
both set, or neither, is a fail-loud boot error.

### Spec caching

**Deferred (not in initial implementation).** Boot fetches the spec
fresh. If the spec host is down, boot fails loud — acceptable because an
API whose spec host is down won't serve traffic anyway. A future
enhancement may add an optional `OAPI_SPEC_CACHE_PATH` to survive
transient spec-host outages; not built now (YAGNI).

### Upstream credentials

One env var per declared scheme, name derived from the **scheme key**
(the identifier under `components.securitySchemes`, which the spec's
`security:` requirements reference — present for every scheme type):

`OAPI_SECURITY_<SCHEMEKEY>` (e.g. scheme key `ApiKeyAuth` →
`OAPI_SECURITY_APIKEYAUTH`).

The **scheme type** dictates how the single value is interpreted and
injected:

| Scheme type (spec) | Value form | Injection | In scope? |
|---|---|---|---|
| `apiKey` (header) | raw key | header at declared `name` | ✅ |
| `apiKey` (query) | raw key | query param at declared `name` | ✅ |
| `http` `bearer` | raw token | `Authorization: Bearer <value>` | ✅ |
| `http` `basic` | `user:pass` | split on first `:`, base64 → `Authorization: Basic <b64>` | ✅ |
| `oauth2` / `openIdConnect` | — | — | ❌ dedicated server |
| `mutualTLS` | — | — | ❌ dedicated server |

The only in-scope two-input scheme is `http basic`; the universal
`username:password` single-string convention keeps it one env var.
Genuinely multi-field schemes (oauth2/oidc/mTLS) fail loud.

### Boot-time validation (fail loud)

After fetching+parsing the spec, compute the set of schemes referenced by
the spec's `security:` requirements and, for each, confirm a supplied
value and a supported type. Refuse to start with a precise message
otherwise. No silent degradation.

## Runtime internals & lifecycle

Module responsibilities (plain-Python core keeps FastMCP types out so it
is unit-testable without a server):

- **`domain.py`** → plain-Python spec/auth core, no FastMCP imports:
  - `load_spec(url | path) -> dict` — fetch/read + parse JSON *or* YAML.
  - `resolve_base_url(spec, override) -> str`.
  - `required_schemes(spec) -> list[SchemeRef]` — only schemes
    referenced by `security:`.
  - `build_upstream_client(spec, base_url, timeout, env_lookup) ->
    httpx.AsyncClient` — resolves each required scheme's value via the
    injected `env_lookup` and installs it (header/query/basic); raises a
    precise error on missing value or unsupported type.
- **`_server_deps.py`** → the lifespan **owns the client's lifetime**: it
  receives the already-built client and `await client.aclose()` in
  `finally`. The `get_service` DI shape stays for the `ping` health
  check.
- **`server.py`** → `make_server()`: load+validate spec → derive
  name/instructions from `info` → build client →
  `providers=[OpenAPIProvider(spec, client)]` in the `FastMCP(...)` call,
  threading the client into the lifespan for cleanup. Uses the existing
  `DOMAIN-WIRING` / `DOMAIN-UPSTREAM` sentinels.
- **`tools.py`** → unchanged `ping`; OpenAPI tools arrive via the
  provider.

### Lifecycle contract (load-bearing ordering)

- Spec is fetched+validated **before** `FastMCP` is constructed — so boot
  fails loud before a half-built server exists, and name/instructions can
  derive from `info`.
- The client is created in `make_server()` (the provider needs it at
  construction) but **owned by the lifespan** for shutdown: close path is
  lifespan `finally` → `client.aclose()`.
- If `make_server()` raises **after** the client is built but **before**
  the lifespan takes ownership, `make_server()` closes the client itself
  — no leaked socket on boot failure.
- Normal shutdown closes the client exactly once; a second close is safe.

### Enumerated failure modes (each becomes a test)

| Failure mode | Contract |
|---|---|
| Spec URL unfetchable / non-2xx | Fail loud at boot, message names the URL |
| Spec body not valid JSON/YAML, or not an OpenAPI doc | Fail loud, message distinguishes parse vs. shape |
| Both `SPEC_URL` and `SPEC_PATH` set, or neither | Fail loud (exactly-one contract) |
| No usable base URL (no override; spec `servers` empty/relative/placeholder) | Fail loud |
| Required scheme has no `OAPI_SECURITY_<KEY>` value | Fail loud, names scheme key + derived env var |
| Required scheme type is `oauth2`/`oidc`/`mTLS` | Fail loud, "use a dedicated server" |
| `basic` value lacks a `:` | Fail loud (needs `user:pass`) |
| Client built, then boot fails downstream | `make_server()` closes the client — no leak |
| Normal shutdown | lifespan closes client exactly once; second close is safe |
| Spec declares a scheme but no operation requires it | Not an error — only *referenced* schemes are validated |

## Testing strategy

Inherits the fleet gate (`ruff check`/`format`, `mypy src/ tests/`,
`pytest`). The plain-Python core carries the bulk of coverage as fast
unit tests:

- **Core unit tests (no network, no server):** `load_spec` (JSON + YAML,
  parse-fail, not-an-OpenAPI-doc); `resolve_base_url` (override wins /
  spec fallback / empty-servers→raise / relative→raise);
  `required_schemes` (only `security:`-referenced schemes returned);
  `build_upstream_client` driven by a spec dict + a fake env lookup,
  asserting the injected header/query/basic per supported type and a
  precise raise for missing-value / unsupported-type / bad-`basic`. One
  test per failure-mode row.
- **Integration test (in-memory, mocked upstream):** tiny fixture spec +
  `httpx.MockTransport` upstream; construct via `make_server()`, connect
  FastMCP's in-memory client, assert the provider's tools list alongside
  `ping`, and that calling one routes to the mock with the credential
  injected. No real sockets.
- **Lifecycle test:** `make_server()` with a fixture spec (via
  `SPEC_PATH` to avoid network); assert the client is closed on lifespan
  exit, and that a boot failure *after* client creation still closes it.
- **Boot-fail tests:** each fail-loud path asserts the server refuses to
  start with its specific message.

Spec fetching stays test-friendly via `SPEC_PATH` + fixture files for
most tests and `MockTransport` where a fetch must be exercised — no test
hits the network.

## Out of scope (initial implementation)

- Curation/route-map tuning for large APIs — make a dedicated sibling.
- `oauth2` / `openIdConnect` / `mutualTLS` upstream auth.
- Spec caching across restarts (`OAPI_SPEC_CACHE_PATH`) — future
  enhancement.
- Inline-spec-in-env source — URL and mounted file only.

## Open items for the sibling repo

- Final repo name and `<PREFIX>` (examples use `openapi-mcp` / `OAPI`).
- Whether `ping` is retained or renamed for this server's identity.
