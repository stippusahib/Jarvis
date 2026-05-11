# JARVIS Tool — System Control
"""System-level tools: screenshot, lock, shutdown, restart, sleep, WiFi, Bluetooth, brightness."""

import platform
import subprocess
from registry import ToolRegistry
from tools.base import BaseTool, ToolResult, ToolParam


@ToolRegistry.register("screenshot")
class ScreenshotTool(BaseTool):
    tool_id = "screenshot"
    name = "Screenshot"
    description = "Take a screenshot and save to Desktop"
    permission_tier = "auto"
    parameters = []

    def execute(self, params: dict) -> ToolResult:
        try:
            import mss
            from pathlib import Path
            import time
            with mss.mss() as sct:
                filename = Path.home() / "Desktop" / f"screenshot_{int(time.time())}.png"
                sct.shot(output=str(filename))
            return ToolResult(content=f"Screenshot saved: {filename}")
        except Exception as e:
            return ToolResult(content=f"Screenshot failed: {e}", success=False)


@ToolRegistry.register("lock_screen")
class LockScreenTool(BaseTool):
    tool_id = "lock_screen"
    name = "Lock Screen"
    description = "Lock the computer screen"
    permission_tier = "auto"
    parameters = []

    def execute(self, params: dict) -> ToolResult:
        try:
            if platform.system() == "Windows":
                import ctypes
                ctypes.windll.user32.LockWorkStation()
            else:
                subprocess.run(["loginctl", "lock-session"])
            return ToolResult(content="Screen locked")
        except Exception as e:
            return ToolResult(content=f"Lock failed: {e}", success=False)


@ToolRegistry.register("shutdown")
class ShutdownTool(BaseTool):
    tool_id = "shutdown"
    name = "Shutdown"
    description = "Shutdown the computer (DESTRUCTIVE)"
    permission_tier = "admin"
    parameters = []

    def execute(self, params: dict) -> ToolResult:
        try:
            if platform.system() == "Windows":
                subprocess.run(["shutdown", "/s", "/t", "5"])
            else:
                subprocess.run(["shutdown", "-h", "now"])
            return ToolResult(content="Shutting down in 5 seconds...")
        except Exception as e:
            return ToolResult(content=f"Shutdown failed: {e}", success=False)


@ToolRegistry.register("restart")
class RestartTool(BaseTool):
    tool_id = "restart"
    name = "Restart"
    description = "Restart the computer (DESTRUCTIVE)"
    permission_tier = "admin"
    parameters = []

    def execute(self, params: dict) -> ToolResult:
        try:
            if platform.system() == "Windows":
                subprocess.run(["shutdown", "/r", "/t", "5"])
            else:
                subprocess.run(["shutdown", "-r", "now"])
            return ToolResult(content="Restarting in 5 seconds...")
        except Exception as e:
            return ToolResult(content=f"Restart failed: {e}", success=False)


@ToolRegistry.register("sleep")
class SleepTool(BaseTool):
    tool_id = "sleep"
    name = "Sleep"
    description = "Put the computer to sleep"
    permission_tier = "confirm"
    parameters = []

    def execute(self, params: dict) -> ToolResult:
        try:
            if platform.system() == "Windows":
                subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
            else:
                subprocess.run(["systemctl", "suspend"])
            return ToolResult(content="Going to sleep...")
        except Exception as e:
            return ToolResult(content=f"Sleep failed: {e}", success=False)


@ToolRegistry.register("wifi_toggle")
class WiFiToggleTool(BaseTool):
    tool_id = "wifi_toggle"
    name = "WiFi Toggle"
    description = "Turn WiFi on or off"
    permission_tier = "confirm"
    parameters = [ToolParam(name="action", description="'on' or 'off'")]

    def execute(self, params: dict) -> ToolResult:
        action = params.get("action", "off").lower()
        state = "enabled" if action == "on" else "disabled"
        try:
            if platform.system() == "Windows":
                subprocess.run(
                    ["netsh", "interface", "set", "interface", "Wi-Fi", state],
                    capture_output=True, timeout=10
                )
            return ToolResult(content=f"WiFi {action}")
        except Exception as e:
            return ToolResult(content=f"WiFi toggle failed: {e}", success=False)


@ToolRegistry.register("bluetooth_toggle")
class BluetoothToggleTool(BaseTool):
    tool_id = "bluetooth_toggle"
    name = "Bluetooth Toggle"
    description = "Turn Bluetooth on or off"
    permission_tier = "confirm"
    parameters = [ToolParam(name="action", description="'on' or 'off'")]

    def execute(self, params: dict) -> ToolResult:
        action = params.get("action", "off").lower()
        try:
            if platform.system() == "Windows":
                # Use PowerShell to toggle Bluetooth radio
                ps_cmd = (
                    "Add-Type -AssemblyName System.Runtime.WindowsRuntime; "
                    "[Windows.Devices.Radios.Radio,Windows.System.Devices,ContentType=WindowsRuntime] | Out-Null; "
                    "$radios = [Windows.Devices.Radios.Radio]::GetRadiosAsync().AsTask().Result; "
                    f"$radios | Where-Object {{$_.Kind -eq 'Bluetooth'}} | "
                    f"ForEach-Object {{$_.SetStateAsync([Windows.Devices.Radios.RadioState]::{'On' if action == 'on' else 'Off'}).AsTask().Wait()}}"
                )
                subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, timeout=15)
            return ToolResult(content=f"Bluetooth {action}")
        except Exception as e:
            return ToolResult(content=f"Bluetooth toggle failed: {e}", success=False)


@ToolRegistry.register("brightness_up")
class BrightnessUpTool(BaseTool):
    tool_id = "brightness_up"
    name = "Brightness Up"
    description = "Increase screen brightness"
    permission_tier = "auto"
    parameters = []

    def execute(self, params: dict) -> ToolResult:
        try:
            import screen_brightness_control as sbc
            current = sbc.get_brightness()[0]
            sbc.set_brightness(min(100, current + 10))
            return ToolResult(content=f"Brightness up to {min(100, current + 10)}%")
        except Exception:
            return ToolResult(content="Brightness control not available", success=False)


@ToolRegistry.register("brightness_down")
class BrightnessDownTool(BaseTool):
    tool_id = "brightness_down"
    name = "Brightness Down"
    description = "Decrease screen brightness"
    permission_tier = "auto"
    parameters = []

    def execute(self, params: dict) -> ToolResult:
        try:
            import screen_brightness_control as sbc
            current = sbc.get_brightness()[0]
            sbc.set_brightness(max(0, current - 10))
            return ToolResult(content=f"Brightness down to {max(0, current - 10)}%")
        except Exception:
            return ToolResult(content="Brightness control not available", success=False)


@ToolRegistry.register("set_brightness")
class SetBrightnessTool(BaseTool):
    tool_id = "set_brightness"
    name = "Set Brightness"
    description = "Set screen brightness to a specific level (0-100)"
    permission_tier = "auto"
    parameters = [ToolParam(name="value", param_type="integer", description="Brightness 0-100")]

    def execute(self, params: dict) -> ToolResult:
        value = max(0, min(100, int(params.get("value", 50))))
        try:
            import screen_brightness_control as sbc
            sbc.set_brightness(value)
            return ToolResult(content=f"Brightness set to {value}%")
        except Exception:
            return ToolResult(content="Brightness control not available", success=False)
