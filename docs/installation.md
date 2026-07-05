# Installation

## From PyPI

```bash
pip install pvliesdonk-openapi-mcp
```

## From Docker

```bash
docker pull ghcr.io/pvliesdonk/openapi-mcp:latest
```

## From source

```bash
git clone https://github.com/pvliesdonk/openapi-mcp
cd openapi-mcp
uv sync --all-extras --all-groups
```

<!-- DOMAIN-INSTALL-EXTRA-START -->
## Linux packages (.deb / .rpm)

Download the `.deb` or `.rpm` package from the
[GitHub Releases](https://github.com/pvliesdonk/openapi-mcp/releases) page. Both
install a hardened systemd unit and source environment configuration from
`/etc/openapi-mcp/env` (copy the shipped `/etc/openapi-mcp/env.example`).

## Claude Desktop (.mcpb bundle)

Download the `.mcpb` bundle from the
[GitHub Releases](https://github.com/pvliesdonk/openapi-mcp/releases) page and
double-click to install, or run:

```bash
mcpb install openapi-mcp-<version>.mcpb
```

For manual setup, see [Claude Desktop deployment](deployment/claude-desktop.md).
<!-- DOMAIN-INSTALL-EXTRA-END -->
