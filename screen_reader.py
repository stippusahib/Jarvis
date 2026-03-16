# PRIVACY: RAM-only. Zero disk I/O.
import mss
import io
import gc
import base64
import queue
import time
import threading
from PIL import Image


class ScreenReader:
    """Captures screen periodically, encodes to base64 JPEG in RAM only."""

    def __init__(self):
        self.output_queue = queue.Queue(maxsize=1)
        self.running = False
        self._overlay_hwnd = None

        # Load device-optimized settings
        try:
            import settings_manager
            profile = settings_manager.get('device_profile', {})
            res = profile.get('capture_resolution', [1280, 720])
            self.capture_width = res[0]
            self.capture_height = res[1]
            self.jpeg_quality = profile.get('jpeg_quality', 55)
            self.interval = profile.get('capture_interval', 8)
        except Exception:
            self.capture_width = 1280
            self.capture_height = 720
            self.jpeg_quality = 55
            self.interval = 8

    def set_overlay_hwnd(self, hwnd):
        """Set the overlay window handle so it can be hidden during capture."""
        self._overlay_hwnd = hwnd

    def start(self):
        """Start screen capture in a background daemon thread."""
        self.running = True
        t = threading.Thread(target=self._capture_loop, daemon=True)
        t.start()

    def _capture_loop(self):
        """Main capture loop — grabs screen, encodes to base64 JPEG."""
        while self.running:
            try:
                # Hide overlay before capture to avoid feedback loop
                try:
                    import ctypes
                    if self._overlay_hwnd:
                        ctypes.windll.user32.ShowWindow(self._overlay_hwnd, 0)  # type: ignore
                except Exception:
                    pass

                with mss.mss() as sct:
                    monitor = sct.monitors[1]
                    screenshot = sct.grab(monitor)
                    img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                    img.thumbnail((self.capture_width, self.capture_height), Image.LANCZOS)
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG", quality=self.jpeg_quality)
                    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

                # Restore overlay after capture
                try:
                    import ctypes
                    if self._overlay_hwnd:
                        ctypes.windll.user32.ShowWindow(self._overlay_hwnd, 5)  # SW_SHOW
                except Exception:
                    pass

                # Drain queue if full, then put new frame
                try:
                    self.output_queue.get_nowait()
                except queue.Empty:
                    pass
                self.output_queue.put(b64)

                del img, buf, screenshot, b64
                gc.collect()

                time.sleep(self.interval)

            except Exception as e:
                print(f"⚠️  Screen capture error: {e}")
                # Ensure overlay is restored even on error
                try:
                    import ctypes
                    if self._overlay_hwnd:
                        ctypes.windll.user32.ShowWindow(self._overlay_hwnd, 5)  # SW_SHOW
                except Exception:
                    pass
                time.sleep(self.interval)
                continue

    def get_latest(self):
        """Get the latest screen capture as base64 string, or None."""
        try:
            return self.output_queue.get_nowait()
        except queue.Empty:
            return None

    def stop(self):
        """Stop screen capture."""
        self.running = False
