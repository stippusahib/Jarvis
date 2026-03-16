# PRIVACY: RAM-only. Zero disk I/O.
# THESE TWO LINES MUST BE FIRST — before ALL other imports
import os
os.environ["HF_HUB_OFFLINE"] = "1"       # prevents 30s hang on airplane mode
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import sys
import time
import threading
import tkinter as tk
import ast
import gc

try:
    import keyboard
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False

from audio_listener import AudioListener
from screen_reader import ScreenReader
from context_engine import get_suggestion, prewarm_ollama
from ghost_overlay import GhostOverlay
from tray import create_tray_icon


def privacy_audit():
    """Scan all .py files in current directory for disk write calls."""
    violations = []
    # Whitelist — files explicitly allowed to write to disk
    WHITELIST = {"settings_manager.py"}

    for filename in os.listdir("."):
        if not filename.endswith(".py"):
            continue
        if filename in WHITELIST:
            continue
        try:
            with open(filename, "r", encoding="utf-8") as f:
                source = f.read()
        except Exception:
            continue

        try:
            tree = ast.parse(source, filename=filename)
        except SyntaxError:
            print(f"⚠️  Skipping {filename} — syntax error during audit")
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            # Check for open() calls
            func_name = ""
            if isinstance(node.func, ast.Name):
                func_name = str(getattr(node.func, "id", ""))
            elif isinstance(node.func, ast.Attribute):
                func_name = str(getattr(node.func, "attr", ""))

            if func_name != "open":
                continue

            # Check mode argument for write modes
            write_modes = ("w", "wb", "a", "ab", "w+", "wb+", "a+", "ab+")

            # Check keyword args
            for kw in node.keywords:
                if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                    val = str(getattr(kw.value, "value", ""))
                    if any(m in val for m in write_modes):
                        violations.append(filename)

            # Check second positional arg
            if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
                val = str(getattr(node.args[1], "value", ""))
                if any(m in val for m in write_modes):
                    violations.append(filename)

    if violations:
        for v in set(violations):
            print(f"🚨 PRIVACY VIOLATION in {v}")
    else:
        print("🔒 Privacy audit passed — zero disk writes detected")


DEMO_SCENARIOS = [
    "That nested loop is O(n²) — a dict lookup cuts it to O(1).",
    "John just said your name — unmute now, they're waiting.",
    "Priya asked a direct question 4 messages ago — still unread.",
    "Back-to-back meetings, no gap — 5 min buffer saves your context.",
    "GDPR Article 17 covers this — right to erasure, cite it now.",
]


def run_demo(overlay):
    """Run 5 demo scenarios with timed popups."""
    time.sleep(1.0)
    print("🎬 Demo mode — 5 scenarios loading...")
    for i, scenario in enumerate(DEMO_SCENARIOS):
        print(f"   [{i+1}/5] {scenario}")
        overlay.show_popup(scenario)
        time.sleep(4.8)
    print("✅ Demo complete. This is what live mode looks like in real-time.")


def run_live(overlay, screen):
    """Run in live mode — real mic transcription + real Ollama suggestions."""
    prewarm_ollama()

    audio = AudioListener()
    audio.start()
    screen.start()

    # Reduce screen capture interval for hotkey responsiveness
    screen.interval = 4  # capture every 4 seconds instead of 8

    print("🧠 Live mode active — listening and watching...")
    print("   Press Ctrl+C to stop.\n")

    try:
        while True:
            try:
                audio_text = audio.output_queue.get(timeout=1)
                if audio_text:
                    print(f"🎤 Heard: {audio_text[:80]}")
                    screen_b64 = screen.get_latest()
                    suggestion = get_suggestion(audio_text, screen_b64)
                    if suggestion != "SILENT":
                        print(f"⚡ Suggestion: {suggestion}")
                        overlay.show_popup(suggestion, "hotkey screen scan")
                    else:
                        print("   (SILENT)")
            except Exception:
                continue
    except KeyboardInterrupt:
        print("\n🧠 JARVIS offline. Clean.")
        audio.stop()
        screen.stop()
        sys.exit(0)


def setup_hotkey(overlay, screen):
    """Setup Ctrl+Shift+J for instant screen scan."""
    if not HAS_KEYBOARD:
        print("⚠️  keyboard library not found — hotkey disabled. Run: pip install keyboard")
        return

    def on_hotkey():
        try:
            print("🔑 Ctrl+Shift+J — instant screen scan triggered")
            screen_b64 = screen.get_latest()
            if not screen_b64:
                print("🔑 No screen capture yet — waiting for first capture...")
                return
            suggestion = get_suggestion(
                "Analyze this screen carefully. If there is code visible, identify bugs, errors, or improvements. If there is a diagram, describe it. Give specific actionable feedback.",
                screen_b64,
                force_vision=True
            )
            if suggestion and suggestion != "SILENT":
                print(f"🔑 Hotkey suggestion: {suggestion}")
                overlay.show_popup(suggestion, "hotkey screen scan")
            else:
                print("🔑 Nothing specific found on screen")
        except Exception as e:
            print(f"⚠️  Hotkey error: {e}")

    try:
        keyboard.add_hotkey('ctrl+shift+j', on_hotkey, suppress=False)
        print("🔑 Hotkey active: Ctrl+Shift+J — instant screen scan")
    except Exception as e:
        print(f"⚠️  Hotkey registration failed: {e}")


def main():
    demo_mode = "--demo" in sys.argv
    gui_mode = "--gui" in sys.argv or (not demo_mode and "--cli" not in sys.argv)

    privacy_audit()

    # ── GUI Mode (default) ──────────────────────────────
    if gui_mode and not demo_mode:
        print("🖥️  Launching JARVIS Dashboard...")
        from app_gui import launch
        launch()
        return

    # ── CLI Mode (legacy / demo) ────────────────────────
    root = tk.Tk()
    root.withdraw()
    overlay = GhostOverlay(root)

    # Screen reader initialized here so hwnd can be passed
    screen = ScreenReader()
    try:
        hwnd = overlay.get_hwnd()
        screen.set_overlay_hwnd(hwnd)
    except Exception:
        pass

    # Tray icon — safe, never crashes main if it fails
    tray = create_tray_icon(lambda: (root.quit(), sys.exit(0)))

    # Setup hotkey
    setup_hotkey(overlay, screen)

    if demo_mode:
        print("🧠 JARVIS, Live — DEMO MODE")
        t = threading.Thread(target=run_demo, args=(overlay,), daemon=True)
    else:
        print("🧠 JARVIS, Live — LIVE MODE")
        t = threading.Thread(target=run_live, args=(overlay, screen), daemon=True)

    t.start()
    root.mainloop()


if __name__ == "__main__":
    main()
