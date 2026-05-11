# JARVIS Tool — Web Tools
"""Web search and URL navigation tools."""

import subprocess
import platform
import webbrowser
from registry import ToolRegistry
from tools.base import BaseTool, ToolResult, ToolParam


@ToolRegistry.register("web_search")
class WebSearchTool(BaseTool):
    tool_id = "web_search"
    name = "Web Search"
    description = "Search the web using the default browser"
    permission_tier = "auto"
    parameters = [ToolParam(name="query", description="Search query")]

    def execute(self, params: dict) -> ToolResult:
        query = params.get("query", "").strip()
        if not query:
            return ToolResult(content="No query provided", success=False)
        try:
            import urllib.parse
            url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
            webbrowser.open(url)
            return ToolResult(content=f"Searching for: {query}")
        except Exception as e:
            return ToolResult(content=f"Search failed: {e}", success=False)


@ToolRegistry.register("open_url")
class OpenURLTool(BaseTool):
    tool_id = "open_url"
    name = "Open URL"
    description = "Open a URL in the default browser"
    permission_tier = "auto"
    parameters = [ToolParam(name="url", description="URL to open")]

    def execute(self, params: dict) -> ToolResult:
        url = params.get("url", "").strip()
        if not url:
            return ToolResult(content="No URL provided", success=False)
        if not url.startswith("http"):
            url = "https://" + url
        try:
            webbrowser.open(url)
            return ToolResult(content=f"Opened {url}")
        except Exception as e:
            return ToolResult(content=f"Failed to open URL: {e}", success=False)
