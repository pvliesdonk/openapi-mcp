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

Document your project-specific variables here.
<!-- DOMAIN-CONFIG-VARS-END -->
