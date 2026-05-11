# JARVIS Tool — Volume & Media Control
"""Volume, mute, and media playback tools."""

import platform
import subprocess
from registry import ToolRegistry
from tools.base import BaseTool, ToolResult, ToolParam


@ToolRegistry.register("volume_up")
class VolumeUpTool(BaseTool):
    tool_id = "volume_up"
    name = "Volume Up"
    description = "Increase system volume"
    permission_tier = "auto"
    parameters = []

    def execute(self, params: dict) -> ToolResult:
        try:
            if platform.system() == "Windows":
                from ctypes import cast, POINTER
                import comtypes
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, comtypes.CLSCTX_ALL, None)
                volume = cast(interface, POINTER(IAudioEndpointVolume))
                current = volume.GetMasterVolumeLevelScalar()
                new_vol = min(1.0, current + 0.1)
                volume.SetMasterVolumeLevelScalar(new_vol, None)
                return ToolResult(content=f"Volume up to {int(new_vol * 100)}%")
            return ToolResult(content="Volume control not supported on this OS", success=False)
        except ImportError:
            # Fallback: use keyboard simulation
            try:
                import keyboard
                keyboard.press_and_release('volume up')
                return ToolResult(content="Volume increased")
            except Exception:
                return ToolResult(content="pycaw not installed — run: pip install pycaw", success=False)
        except Exception as e:
            return ToolResult(content=f"Volume error: {e}", success=False)


@ToolRegistry.register("volume_down")
class VolumeDownTool(BaseTool):
    tool_id = "volume_down"
    name = "Volume Down"
    description = "Decrease system volume"
    permission_tier = "auto"
    parameters = []

    def execute(self, params: dict) -> ToolResult:
        try:
            if platform.system() == "Windows":
                from ctypes import cast, POINTER
                import comtypes
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, comtypes.CLSCTX_ALL, None)
                volume = cast(interface, POINTER(IAudioEndpointVolume))
                current = volume.GetMasterVolumeLevelScalar()
                new_vol = max(0.0, current - 0.1)
                volume.SetMasterVolumeLevelScalar(new_vol, None)
                return ToolResult(content=f"Volume down to {int(new_vol * 100)}%")
            return ToolResult(content="Volume control not supported on this OS", success=False)
        except ImportError:
            try:
                import keyboard
                keyboard.press_and_release('volume down')
                return ToolResult(content="Volume decreased")
            except Exception:
                return ToolResult(content="pycaw not installed", success=False)
        except Exception as e:
            return ToolResult(content=f"Volume error: {e}", success=False)


@ToolRegistry.register("set_volume")
class SetVolumeTool(BaseTool):
    tool_id = "set_volume"
    name = "Set Volume"
    description = "Set system volume to a specific percentage (0-100)"
    permission_tier = "auto"
    parameters = [
        ToolParam(name="value", param_type="integer", description="Volume level 0-100"),
    ]

    def execute(self, params: dict) -> ToolResult:
        value = params.get("value", 50)
        try:
            value = int(value)
            value = max(0, min(100, value))
        except (ValueError, TypeError):
            value = 50

        try:
            if platform.system() == "Windows":
                from ctypes import cast, POINTER
                import comtypes
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, comtypes.CLSCTX_ALL, None)
                volume = cast(interface, POINTER(IAudioEndpointVolume))
                volume.SetMasterVolumeLevelScalar(value / 100.0, None)
                return ToolResult(content=f"Volume set to {value}%")
            return ToolResult(content="Not supported on this OS", success=False)
        except Exception as e:
            return ToolResult(content=f"Volume error: {e}", success=False)


@ToolRegistry.register("mute")
class MuteTool(BaseTool):
    tool_id = "mute"
    name = "Mute"
    description = "Mute system audio"
    permission_tier = "auto"
    parameters = []

    def execute(self, params: dict) -> ToolResult:
        try:
            if platform.system() == "Windows":
                from ctypes import cast, POINTER
                import comtypes
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, comtypes.CLSCTX_ALL, None)
                volume = cast(interface, POINTER(IAudioEndpointVolume))
                volume.SetMute(1, None)
                return ToolResult(content="Audio muted")
            return ToolResult(content="Not supported", success=False)
        except Exception as e:
            return ToolResult(content=f"Mute error: {e}", success=False)


@ToolRegistry.register("unmute")
class UnmuteTool(BaseTool):
    tool_id = "unmute"
    name = "Unmute"
    description = "Unmute system audio"
    permission_tier = "auto"
    parameters = []

    def execute(self, params: dict) -> ToolResult:
        try:
            if platform.system() == "Windows":
                from ctypes import cast, POINTER
                import comtypes
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, comtypes.CLSCTX_ALL, None)
                volume = cast(interface, POINTER(IAudioEndpointVolume))
                volume.SetMute(0, None)
                return ToolResult(content="Audio unmuted")
            return ToolResult(content="Not supported", success=False)
        except Exception as e:
            return ToolResult(content=f"Unmute error: {e}", success=False)


@ToolRegistry.register("play_pause")
class PlayPauseTool(BaseTool):
    tool_id = "play_pause"
    name = "Play/Pause"
    description = "Toggle play/pause for media playback"
    permission_tier = "auto"
    parameters = []

    def execute(self, params: dict) -> ToolResult:
        try:
            import keyboard
            keyboard.press_and_release('play/pause media')
            return ToolResult(content="Toggled play/pause")
        except Exception as e:
            return ToolResult(content=f"Media control error: {e}", success=False)


@ToolRegistry.register("next_track")
class NextTrackTool(BaseTool):
    tool_id = "next_track"
    name = "Next Track"
    description = "Skip to next media track"
    permission_tier = "auto"
    parameters = []

    def execute(self, params: dict) -> ToolResult:
        try:
            import keyboard
            keyboard.press_and_release('next track')
            return ToolResult(content="Skipped to next track")
        except Exception as e:
            return ToolResult(content=f"Media control error: {e}", success=False)


@ToolRegistry.register("prev_track")
class PrevTrackTool(BaseTool):
    tool_id = "prev_track"
    name = "Previous Track"
    description = "Go to previous media track"
    permission_tier = "auto"
    parameters = []

    def execute(self, params: dict) -> ToolResult:
        try:
            import keyboard
            keyboard.press_and_release('previous track')
            return ToolResult(content="Went to previous track")
        except Exception as e:
            return ToolResult(content=f"Media control error: {e}", success=False)
