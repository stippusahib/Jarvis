# PRIVACY: RAM-only. Zero disk I/O.
import tkinter as tk
import queue


class GhostOverlay:
    """Ghost HUD popup — bottom-right overlay with fade in/out animations."""

    def __init__(self, root):
        self.root = root
        self.popup_queue = queue.Queue()
        self.showing = False
        self._after_id = None
        self._fade_after_id = None

        # Window setup — frameless, always-on-top, fully transparent initially
        root.overrideredirect(True)
        root.attributes('-topmost', True)
        root.attributes('-alpha', 0.0)
        root.configure(bg='#0A0A0A')
        root.withdraw()

        # Do NOT use: root.attributes('-transparentcolor', ...)
        # Alpha fade handles visibility — bg #0A0A0A is near-black, looks correct

        # Layout
        outer = tk.Frame(root, bg='#1C1C1C', padx=1, pady=1)
        outer.pack(fill='both', expand=True)

        inner = tk.Frame(outer, bg='#0A0A0A', padx=16, pady=12)
        inner.pack(fill='both', expand=True)

        self.label_header = tk.Label(
            inner, text="⚡  SECOND BRAIN",
            font=("Courier New", 9, "bold"),
            fg='#3A3A3A', bg='#0A0A0A', anchor='w'
        )
        self.label_header.pack(fill='x', pady=(0, 6))

        self.label_text = tk.Label(
            inner, text="",
            font=("Courier New", 12),
            fg='#E8FF47', bg='#0A0A0A',
            wraplength=340, justify='left', anchor='w'
        )
        self.label_text.pack(fill='x')

        # Click to dismiss
        root.bind("<Button-1>", lambda e: self._dismiss_now())

        # Start polling the queue
        self._poll_queue()

    def get_hwnd(self):
        """Expose window handle for screen capture exclusion."""
        try:
            return self.root.winfo_id()
        except Exception:
            return None

    def _poll_queue(self):
        """Poll for new popup text from the thread-safe queue."""
        try:
            text = self.popup_queue.get_nowait()
            self._show(text)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)

    def show_popup(self, text):
        """Thread-safe method to queue a popup message."""
        self.popup_queue.put(text)

    def _show(self, text):
        """Display a new popup with fade-in animation."""
        # Cancel any active timers
        if self._after_id:
            self.root.after_cancel(self._after_id)
            self._after_id = None
        if self._fade_after_id:
            self.root.after_cancel(self._fade_after_id)
            self._fade_after_id = None

        self.label_text.config(text=text)

        # Position: bottom-right corner
        self.root.update_idletasks()
        w = max(self.root.winfo_reqwidth(), 400)
        h = max(self.root.winfo_reqheight(), 75)
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = sw - w - 24
        y = sh - h - 60
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        self.root.deiconify()
        self.showing = True
        self._fade_in(0)

    def _fade_in(self, step):
        """Fade in over 200ms (15 steps × ~13ms)."""
        alpha = (step / 15) * 0.88
        self.root.attributes('-alpha', alpha)
        if step < 15:
            self._fade_after_id = self.root.after(13, lambda: self._fade_in(step + 1))
        else:
            self._after_id = self.root.after(4000, self._start_fade_out)

    def _start_fade_out(self):
        """Begin fade out."""
        self._fade_out(20)

    def _fade_out(self, step):
        """Fade out over 300ms (20 steps × 15ms)."""
        alpha = (step / 20) * 0.88
        self.root.attributes('-alpha', alpha)
        if step > 0:
            self._fade_after_id = self.root.after(15, lambda: self._fade_out(step - 1))
        else:
            self.root.withdraw()
            self.root.attributes('-alpha', 0.0)
            self.showing = False

    def _dismiss_now(self):
        """Immediately dismiss the popup on click."""
        if self._after_id:
            self.root.after_cancel(self._after_id)
            self._after_id = None
        if self._fade_after_id:
            self.root.after_cancel(self._fade_after_id)
            self._fade_after_id = None
        self.root.attributes('-alpha', 0.0)
        self.root.withdraw()
        self.showing = False
