# JARVIS OS Controller — Shim
"""
Backward-compatibility shim for OSController.
Delegates all execution to the new modular ToolRegistry.
"""
from tools.base import ToolExecutor
from tools import get_all_tools


class OSController:
    """Central executor that routes commands to modular tools."""

    def __init__(self):
        # Initialize the tool executor with all registered tools
        self.executor = ToolExecutor(get_all_tools())

    def execute(self, intent: str, params: dict) -> dict:
        """Execute a command by intent name. Returns {success, message, data}."""
        tool = self.executor.get_tool(intent)
        
        if not tool:
            # Special case for "read_screen" which might be handled elsewhere
            if intent == "read_screen":
                return {"success": False, "message": "Screen reading is handled by GhostOverlay"}
            return {"success": False, "message": f"Unknown command: {intent}"}

        # Convert ToolResult to the legacy dictionary format expected by the system
        result = self.executor.execute(intent, params)
        
        return {
            "success": result.success,
            "message": result.content,
            "data": result.metadata.get("data") if result.metadata else None
        }

