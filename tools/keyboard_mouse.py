# JARVIS Tool — Keyboard & Mouse Control
"""Keyboard typing, key presses, and scrolling tools."""

from registry import ToolRegistry
from tools.base import BaseTool, ToolResult, ToolParam


@ToolRegistry.register("type_text")
class TypeTextTool(BaseTool):
    tool_id = "type_text"
    name = "Type Text"
    description = "Type text using the keyboard"
    permission_tier = "confirm"
    parameters = [ToolParam(name="text", description="Text to type")]

    def execute(self, params: dict) -> ToolResult:
        text = params.get("text", "")
        if not text:
            return ToolResult(content="No text provided", success=False)
        try:
            import keyboard
            keyboard.write(text, delay=0.02)
            return ToolResult(content=f"Typed: {text[:50]}...")
        except Exception as e:
            return ToolResult(content=f"Typing failed: {e}", success=False)


@ToolRegistry.register("press_key")
class PressKeyTool(BaseTool):
    tool_id = "press_key"
    name = "Press Key"
    description = "Press a keyboard key or combination (e.g. ctrl+s, enter)"
    permission_tier = "auto"
    parameters = [ToolParam(name="keys", description="Key combo like 'ctrl+s'")]

    def execute(self, params: dict) -> ToolResult:
        keys = params.get("keys", "").strip()
        if not keys:
            return ToolResult(content="No keys specified", success=False)
        try:
            import keyboard
            keyboard.press_and_release(keys)
            return ToolResult(content=f"Pressed {keys}")
        except Exception as e:
            return ToolResult(content=f"Key press failed: {e}", success=False)


@ToolRegistry.register("scroll_down")
class ScrollDownTool(BaseTool):
    tool_id = "scroll_down"
    name = "Scroll Down"
    description = "Scroll the page down"
    permission_tier = "auto"
    parameters = []

    def execute(self, params: dict) -> ToolResult:
        try:
            import pyautogui
            pyautogui.scroll(-5)
            return ToolResult(content="Scrolled down")
        except ImportError:
            try:
                import keyboard
                keyboard.press_and_release('page down')
                return ToolResult(content="Scrolled down")
            except Exception as e:
                return ToolResult(content=f"Scroll failed: {e}", success=False)


@ToolRegistry.register("scroll_up")
class ScrollUpTool(BaseTool):
    tool_id = "scroll_up"
    name = "Scroll Up"
    description = "Scroll the page up"
    permission_tier = "auto"
    parameters = []

    def execute(self, params: dict) -> ToolResult:
        try:
            import pyautogui
            pyautogui.scroll(5)
            return ToolResult(content="Scrolled up")
        except ImportError:
            try:
                import keyboard
                keyboard.press_and_release('page up')
                return ToolResult(content="Scrolled up")
            except Exception as e:
                return ToolResult(content=f"Scroll failed: {e}", success=False)
