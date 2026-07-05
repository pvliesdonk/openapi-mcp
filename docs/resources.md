# Resources

MCP resources expose read-only data to clients by URI. See the
[FastMCP resources documentation](https://gofastmcp.com/servers/resources)
for the full resource API.

<!-- DOMAIN-RESOURCES-LIST-START -->
## Built-in resources

### `status://openapi-mcp`

Static resource that reports whether the service is ready. Reading it returns a
JSON object:

```json
{ "ready": true }
```

`ready` is `true` once the service has started and `false` otherwise. The
resource is registered in `src/openapi_mcp/resources.py`.
<!-- DOMAIN-RESOURCES-LIST-END -->
