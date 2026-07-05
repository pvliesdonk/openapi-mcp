# Prompts

MCP prompts are reusable prompt templates exposed to clients. The scaffold
ships a minimal set defined in `src/openapi_mcp/prompts.py`; add
domain-specific prompts there and document them in this page.

## Example

```python
@mcp.prompt()
def summarize(topic: str) -> str:
    """Summarize the given topic in three sentences."""
    return f"Write a three-sentence summary of: {topic}"
```

See the [FastMCP prompts documentation](https://gofastmcp.com/servers/prompts)
for the full prompt API.

<!-- DOMAIN-PROMPTS-LIST-START -->
## Built-in prompts

### `summarize`

Reusable prompt template that asks the model for a one-paragraph summary of the
supplied text.

| Argument | Type | Required | Description |
|---|---|---|---|
| `context` | `str` | Yes | The source text the summary is generated from. |

It returns the prompt string `Summarize the following in one paragraph:` followed
by the supplied `context`. Defined in `src/openapi_mcp/prompts.py`.
<!-- DOMAIN-PROMPTS-LIST-END -->
