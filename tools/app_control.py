# JARVIS Tool — App Control (open, close, switch applications)
"""App lifecycle tools — open, close, and switch between applications."""

import subprocess
import platform
from registry import ToolRegistry
from tools.base import BaseTool, ToolResult, ToolParam


@ToolRegistry.register("open_app")
class OpenAppTool(BaseTool):
    tool_id = "open_app"
    name = "Open Application"
    description = "Open/launch an application by name"
    permission_tier = "auto"
    parameters = [
        ToolParam(name="target", description="Name of the application to open"),
    ]

    # Common app aliases → executable mappings (Windows)
    APP_MAP = {
        "chrome": "chrome", "google chrome": "chrome",
        "firefox": "firefox",
        "edge": "msedge", "microsoft edge": "msedge",
        "notepad": "notepad",
        "calculator": "calc", "calc": "calc",
        "explorer": "explorer", "file explorer": "explorer",
        "terminal": "wt", "windows terminal": "wt",
        "cmd": "cmd", "command prompt": "cmd",
        "powershell": "powershell",
        "code": "code", "vs code": "code", "vscode": "code",
        "spotify": "spotify",
        "discord": "discord",
        "slack": "slack",
        "teams": "teams", "microsoft teams": "teams",
        "word": "winword", "microsoft word": "winword",
        "excel": "excel", "microsoft excel": "excel",
        "powerpoint": "powerpnt",
        "paint": "mspaint",
        "snipping tool": "snippingtool",
        "task manager": "taskmgr",
        "settings": "ms-settings:",
        "control panel": "control",
    }

    def execute(self, params: dict) -> ToolResult:
        target = params.get("target", "").strip().lower()
        if not target:
            return ToolResult(content="No app name provided", success=False)

        exe = self.APP_MAP.get(target, target)

        try:
            if platform.system() == "Windows":
                # Use start for UWP/Store apps, subprocess for others
                if exe.startswith("ms-"):
                    subprocess.Popen(["cmd", "/c", "start", exe], shell=True)
                else:
                    subprocess.Popen(["cmd", "/c", "start", "", exe], shell=True)
            else:
                subprocess.Popen([exe])

            return ToolResult(content=f"Opened {target}", success=True)
        except Exception as e:
            return ToolResult(content=f"Failed to open {target}: {e}", success=False)


@ToolRegistry.register("close_app")
class CloseAppTool(BaseTool):
    tool_id = "close_app"
    name = "Close Application"
    description = "Close/kill a running application by name"
    permission_tier = "confirm"
    parameters = [
        ToolParam(name="target", description="Name of the application to close"),
    ]

    def execute(self, params: dict) -> ToolResult:
        target = params.get("target", "").strip()
        if not target:
            return ToolResult(content="No app name provided", success=False)

        try:
            if platform.system() == "Windows":
                # Try graceful close first, then force
                process_name = target.lower()
                if not process_name.endswith(".exe"):
                    process_name += ".exe"
                subprocess.run(
                    ["taskkill", "/IM", process_name, "/F"],
                    capture_output=True, timeout=5
                )
                return ToolResult(content=f"Closed {target}", success=True)
            else:
                subprocess.run(["pkill", "-f", target], timeout=5)
                return ToolResult(content=f"Closed {target}", success=True)
        except Exception as e:
            return ToolResult(content=f"Failed to close {target}: {e}", success=False)


@ToolRegistry.register("switch_app")
class SwitchAppTool(BaseTool):
    tool_id = "switch_app"
    name = "Switch Application"
    description = "Switch focus to a running application window"
    permission_tier = "auto"
    parameters = [
        ToolParam(name="target", description="Name of the application to switch to"),
    ]

    def execute(self, params: dict) -> ToolResult:
        target = params.get("target", "").strip()
        if not target:
            return ToolResult(content="No app name provided", success=False)

        try:
            import pygetwindow as gw
            windows = gw.getWindowsWithTitle(target)
            if windows:
                win = windows[0]
                if win.isMinimized:
                    win.restore()
                win.activate()
                return ToolResult(content=f"Switched to {target}", success=True)
            return ToolResult(content=f"No window found for '{target}'", success=False)
        except ImportError:
            return ToolResult(content="pygetwindow not installed — cannot switch apps", success=False)
        except Exception as e:
            return ToolResult(content=f"Failed to switch to {target}: {e}", success=False)
