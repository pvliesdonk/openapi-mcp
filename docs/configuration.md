# Configuration

OpenAPI MCP is configured via environment variables with the
``OAPI_`` prefix.

## Common variables

See `fastmcp-pvl-core`'s README for the full list of universal
variables (`OAPI_TRANSPORT`, `OAPI_HOST`,
`OAPI_PORT`, `OAPI_HTTP_PATH`,
`OAPI_BASE_URL`, auth vars, etc.).

## Server identity

These two are read by the scaffold's `make_server()` (not by
`ServerConfig`), so an operator can rename an instance or override its
instructions without editing template-owned code:

- `OAPI_SERVER_NAME`: the server name reported to clients and
  by `get_server_info`. Defaults to `openapi-mcp`.
- `OAPI_INSTRUCTIONS`: replaces the default MCP instructions
  text. Unset, the scaffold builds the default (which advertises this
  override).

<!-- DOMAIN-CONFIG-VARS-START -->
## Domain variables

`openapi-mcp` derives its tools from an OpenAPI spec at boot. Configure the
spec source, upstream base URL, timeout, and per-scheme upstream credentials
via these `OAPI_*` variables (see `.env.example` for a copy-paste template).

| Variable | Purpose | Default |
|---|---|---|
| `OAPI_SPEC_URL` | URL of the OpenAPI spec, fetched at boot | — (exactly one of URL/PATH) |
| `OAPI_SPEC_PATH` | Local/mounted spec file (JSON or YAML), alternative to the URL | — (exactly one of URL/PATH) |
| `OAPI_API_BASE_URL` | Override the upstream base URL | spec `servers[0].url` |
| `OAPI_HTTP_TIMEOUT` | Upstream request timeout (seconds) | `30` |
| `OAPI_SECURITY_<SCHEMEKEY>` | Credential for a referenced security scheme, named by its uppercased key | — (required if the scheme is referenced) |

**Exactly one** of `OAPI_SPEC_URL` / `OAPI_SPEC_PATH` must be set; both or
neither is a fail-loud boot error.

### Upstream credentials

One variable per security scheme **referenced** by the spec's `security:`
requirements, named `OAPI_SECURITY_<SCHEMEKEY-UPPERCASED>`. The scheme *type*
determines how the value is interpreted:

| Scheme type | Value form | In scope? |
|---|---|---|
| `apiKey` (header or query) | raw key | yes |
| `http` `bearer` | raw token | yes |
| `http` `basic` | `user:pass` (split on the first colon) | yes |
| `oauth2` / `openIdConnect` / `mutualTLS` | — | no — use a dedicated server |

This server requires a credential for **every** scheme referenced by any
`security:` requirement; it does not resolve "scheme A *or* B" alternatives.
A spec offering mutually exclusive auth alternatives, or any
`oauth2`/`openIdConnect`/`mutualTLS` scheme, is out of scope — use a
purpose-built sibling scaffolded from `fastmcp-server-template`.
<!-- DOMAIN-CONFIG-VARS-END -->
