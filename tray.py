# PRIVACY: RAM-only. Zero disk I/O.
import threading
import sys
from PIL import Image, ImageDraw


def create_tray_icon(stop_callback):
    """Create a system tray icon. Returns the icon object or None if tray is unavailable.

    The entire function is wrapped in try/except so a tray failure NEVER crashes
    the main app — just prints a warning and continues.
    """
    try:
        # Import pystray INSIDE try block so ImportError is caught gracefully
        import pystray

        # Generate icon image entirely in RAM (never write to disk)
        img = Image.new("RGB", (64, 64), color="#0A0A0A")
        draw = ImageDraw.Draw(img)
        draw.ellipse([8, 8, 56, 56], fill="#E8FF47")
        draw.text((20, 18), "JV", fill="#0A0A0A")

        icon = pystray.Icon(
            name="JARVIS, Live",
            icon=img,
            title="JARVIS — watching silently",
            menu=pystray.Menu(
                pystray.MenuItem("JARVIS, Live — Active", lambda icon, item: None, enabled=False),
                pystray.MenuItem("Quit", lambda icon, item: stop_callback())
            )
        )

        # Start in daemon thread
        threading.Thread(target=icon.run, daemon=True).start()
        print("🔵 System tray icon active")
        return icon

    except Exception as e:
        print(f"⚠️  Tray icon unavailable: {e} — continuing without it")
        return None
