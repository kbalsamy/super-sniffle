"""Tiny stdio MCP server for manually testing heybro's /mcp support offline.

Usage:
    /mcp add test env/bin/python3 src/test_mcp_server.py
    /mcp tools
    what is 17 plus 25?
"""

from mcp.server.mcpserver import MCPServer

server = MCPServer("test-server")


@server.tool()
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


@server.tool()
def echo(text: str) -> str:
    """Echo the given text back."""
    return f"echo: {text}"


if __name__ == "__main__":
    server.run(transport="stdio")
