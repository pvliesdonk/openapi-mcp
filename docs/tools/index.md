# Tools

The tools registered in this server are listed below. See the
[FastMCP tools documentation](https://gofastmcp.com/servers/tools)
for the full tool API.

<!-- DOMAIN-TOOLS-LIST-START -->
## Spec-derived tools

`openapi-mcp` generates its domain tools at runtime from the configured
OpenAPI spec (via FastMCP's `OpenAPIProvider`): every operation in the spec
becomes an MCP tool, named from its `operationId`. The exact tool set depends
on the spec each deployment is pointed at, so it is not enumerated here.

## ping

Health-check tool that returns `"pong"` if the service is alive. Retained as
the fleet-standard liveness check alongside the spec-derived tools.

## get_server_info

Reports the running build so operators can confirm which version is deployed.
The response carries `server_name`, `server_version`, and `core_version` (the
`fastmcp-pvl-core` version). Registered automatically by `make_server()` through
`register_server_info_tool`.
<!-- DOMAIN-TOOLS-LIST-END -->
