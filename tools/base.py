# JARVIS Tool Base — Abstract tool interface for modular plugins.
# Adapted from OpenJarvis tools/_stubs.py
"""
Abstract base class for all JARVIS tools.

Every tool (app control, volume, file ops, etc.) inherits from BaseTool
and registers itself via @ToolRegistry.register(). The agent loop
discovers tools at runtime and builds LLM-compatible descriptions.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ToolResult:
    """Result returned by a tool execution."""
    content: str               # Human-readable output
    success: bool = True       # Whether the tool succeeded
    tool_name: str = ""        # Which tool produced this
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolParam:
    """A single parameter for a tool."""
    name: str
    param_type: str = "string"   # "string", "integer", "boolean", "float"
    description: str = ""
    required: bool = True
    default: Any = None


class BaseTool(ABC):
    """Abstract base class for all JARVIS tools.

    Subclasses must define:
        - tool_id: unique string identifier
        - name: human-readable name
        - description: what this tool does (shown to the LLM)
        - permission_tier: "auto", "confirm", or "admin"
        - parameters: list of ToolParam
        - execute(): the actual logic
    """

    tool_id: str = ""
    name: str = ""
    description: str = ""
    permission_tier: str = "auto"  # "auto", "confirm", "admin"
    parameters: List[ToolParam] = []

    @abstractmethod
    def execute(self, params: Dict[str, Any]) -> ToolResult:
        """Execute the tool with the given parameters.

        Args:
            params: Dictionary of parameter name → value

        Returns:
            ToolResult with the output
        """
        ...

    def get_schema(self) -> Dict[str, Any]:
        """Return OpenAI-compatible function schema for LLM tool-calling."""
        properties = {}
        required = []

        for p in self.parameters:
            prop: Dict[str, Any] = {"type": p.param_type, "description": p.description}
            properties[p.name] = prop
            if p.required:
                required.append(p.name)

        return {
            "type": "function",
            "function": {
                "name": self.tool_id,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                }
            }
        }

    def __repr__(self) -> str:
        return f"Tool({self.tool_id}, tier={self.permission_tier})"


def build_tool_descriptions(tools: List[BaseTool]) -> str:
    """Build a formatted tool description string for the LLM system prompt.

    Returns something like:
        Available tools:
        - open_app(target): Open an application. [auto]
        - delete_file(target): Delete a file. [admin]
    """
    if not tools:
        return ""

    lines = ["Available tools:"]
    for tool in tools:
        params_str = ", ".join(p.name for p in tool.parameters)
        tier_tag = f"[{tool.permission_tier}]"
        lines.append(f"  - {tool.tool_id}({params_str}): {tool.description} {tier_tag}")

    return "\n".join(lines)


class ToolExecutor:
    """Executes tool calls by name, with permission checking.

    This is the bridge between the agent loop and the tool registry.
    """

    def __init__(self, tools: List[BaseTool]):
        self._tools: Dict[str, BaseTool] = {t.tool_id: t for t in tools}

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Look up a tool by ID."""
        return self._tools.get(name)

    def execute(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        """Execute a tool by name with the given arguments."""
        tool = self._tools.get(tool_name)
        if not tool:
            return ToolResult(
                content=f"Unknown tool: {tool_name}",
                success=False,
                tool_name=tool_name,
            )

        try:
            result = tool.execute(arguments)
            result.tool_name = tool.tool_id
            return result
        except Exception as e:
            return ToolResult(
                content=f"Tool '{tool_name}' failed: {e}",
                success=False,
                tool_name=tool_name,
            )

    def get_openai_tools(self) -> List[Dict[str, Any]]:
        """Return OpenAI-format tool definitions for all tools."""
        return [tool.get_schema() for tool in self._tools.values()]

    @property
    def tool_list(self) -> List[BaseTool]:
        return list(self._tools.values())


__all__ = [
    "BaseTool",
    "ToolResult",
    "ToolParam",
    "ToolExecutor",
    "build_tool_descriptions",
]
