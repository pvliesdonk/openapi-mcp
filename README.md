# openapi-mcp

A generic [MCP](https://modelcontextprotocol.io/) server that builds its
tools **at runtime from any OpenAPI specification** — no per-API code.
Point one container image at a spec (URL or mounted file) plus upstream
credentials, and it exposes that API's operations as MCP tools.

A member of the `fastmcp-pvl-core` fleet, scaffolded from
[`fastmcp-server-template`](https://github.com/pvliesdonk/fastmcp-server-template).
It inherits the fleet's inbound auth, config, CI, Docker, and packaging
verbatim; the only difference from a hand-written sibling is that the
domain tools are derived from the spec via FastMCP's `OpenAPIProvider`
rather than written by hand.

Intended for **simple** APIs where a dedicated server isn't worth the
effort. Large or complex APIs — or ones using `oauth2`/`openIdConnect`
upstream auth — are better served by a purpose-built sibling.

## Status

🚧 Design stage. The full design lives at
[`docs/superpowers/specs/2026-07-04-openapi-generic-wrapper-design.md`](docs/superpowers/specs/2026-07-04-openapi-generic-wrapper-design.md).
Implementation has not started.

## License

[MIT](LICENSE)
