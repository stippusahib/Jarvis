# JARVIS Tools Package — Auto-discovers and registers tool plugins.
"""
Tool plugin auto-discovery.

Import this package to register all built-in tools into the ToolRegistry.
Each tool module registers itself via @ToolRegistry.register() on import.
"""

from registry import ToolRegistry
from tools.base import BaseTool, ToolResult, ToolExecutor, build_tool_descriptions

# Auto-import all tool modules so they self-register
from tools import app_control
from tools import volume_control
from tools import file_ops
from tools import system_control
from tools import keyboard_mouse
from tools import web_tools


def get_all_tools() -> list:
    """Return instances of all registered tools."""
    tools = []
    for key in ToolRegistry.keys():
        cls = ToolRegistry.get(key)
        tools.append(cls())
    return tools


__all__ = [
    "BaseTool",
    "ToolResult",
    "ToolExecutor",
    "ToolRegistry",
    "build_tool_descriptions",
    "get_all_tools",
]
