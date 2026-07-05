# OpenAPI MCP

A generic MCP server that builds its tools at runtime from any OpenAPI specification.

## Getting started

- [Installation](installation.md)
- [Configuration](configuration.md)
- [Tools](tools/index.md)

<!-- DOMAIN-INDEX-FEATURES-START -->
## Features

`openapi-mcp` builds its MCP tools at runtime from any OpenAPI specification,
with no per-API code. Point one container image at a spec (a URL or a mounted
file) plus upstream credentials, and it exposes the operations of that API as
MCP tools through FastMCP's `OpenAPIProvider`.

It is intended for simple APIs. Large or complex APIs, or ones using
`oauth2`/`openIdConnect`/`mutualTLS` upstream auth, are better served by a
purpose-built sibling. See [Configuration](configuration.md) for the full
`OAPI_*` contract.
<!-- DOMAIN-INDEX-FEATURES-END -->

<!-- DOMAIN-INDEX-USE-CASES-START -->
## What you can do

The tool surface is whatever the mounted OpenAPI spec defines: each operation
becomes one MCP tool, named by its `operationId`. The concrete prompts depend
on the API you wrap. With a spec mounted, you can ask Claude to:

- **Call an operation directly:** "List the open orders" runs the spec's
  `list_orders` operation and returns the response.
- **Chain operations:** "Find the customer named Acme, then show their most
  recent invoice" composes a search operation with a lookup operation.
- **Confirm the deployment:** "Which server version is running?" calls the
  built-in `get_server_info` tool.

Point the server at a different spec and the tool surface changes with no code
edits.
<!-- DOMAIN-INDEX-USE-CASES-END -->
