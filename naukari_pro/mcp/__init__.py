"""NaukariPro MCP server — expose tools to Grok Bot, Muse, Antigravity, Claude Code, Cursor."""

from naukari_pro.mcp.server import TOOLS, handle_tool, list_tools

__all__ = ["TOOLS", "handle_tool", "list_tools"]
