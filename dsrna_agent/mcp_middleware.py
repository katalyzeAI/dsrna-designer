"""MCP Middleware - Loads tools from MCP servers defined in mcp_config.json."""

import asyncio
import json
from pathlib import Path
from typing import Any

from langchain_core.tools import BaseTool

PROJECT_ROOT = Path(__file__).parent.parent
MCP_CONFIG_PATH = PROJECT_ROOT / "mcp_config.json"


def load_mcp_tools() -> list[BaseTool]:
    """Load tools from MCP servers defined in mcp_config.json."""
    if not MCP_CONFIG_PATH.exists():
        return []

    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
    except ImportError:
        print("Warning: langchain-mcp-adapters not installed, skipping MCP tools")
        return []

    with open(MCP_CONFIG_PATH) as f:
        config = json.load(f)

    servers = config.get("mcpServers", {})
    if not servers:
        return []

    connections = {}
    for name, server_config in servers.items():
        url = server_config.get("url")
        transport = server_config.get("transport", "http")
        if url and transport in ("http", "sse"):
            connections[name] = {"url": url, "transport": "streamable_http"}

    if not connections:
        return []

    async def get_tools():
        client = MultiServerMCPClient(connections, tool_name_prefix=True)
        tools = await client.get_tools()
        return tools

    try:
        return asyncio.run(get_tools())
    except Exception as e:
        print(f"Warning: Failed to load MCP tools: {e}")
        return []


class MCPToolsMiddleware:
    """Middleware that injects MCP tools into the agent."""

    def __init__(self):
        self._tools = None

    @property
    def tools(self) -> list[BaseTool]:
        if self._tools is None:
            self._tools = load_mcp_tools()
        return self._tools

    def get_system_prompt_addition(self) -> str:
        """Return additional system prompt content describing MCP tools."""
        if not self.tools:
            return ""

        tool_list = "\n".join(f"- `{t.name}`: {t.description[:100]}..." for t in self.tools)
        return f"""
## MCP Tools Available

The following tools are loaded from MCP servers:

{tool_list}

Use these tools for their specialized functions (e.g., PubMed for scientific literature).
"""
