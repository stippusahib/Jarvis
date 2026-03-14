# PRIVACY: RAM-only. Zero disk I/O.
import tkinter as tk
import queue
import psutil

try:
    import pygetwindow as gw
    HAS_PYGETWINDOW = True
except ImportError:
    HAS_PYGETWINDOW = False

# --- CONSTANTS ---
class HistoryPanel:
    """Persistent side panel that stores clicked suggestions."""
    def __init__(self, parent_root):
        self.window = tk.Toplevel(parent_root)
        self.window.title("JARVIS History")
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)
        self.window.attributes('-alpha', 0.95)
        self.window.configure(bg='#0D1117')
        
        # Border
        outer = tk.Frame(self.window, bg='#3A3A3A', padx=1, pady=1)
        outer.pack(fill='both', expand=True)
        
        self.inner = tk.Frame(outer, bg='#0D1117', padx=12, pady=12)
        self.inner.pack(fill='both', expand=True)
        
        # Header area with close button
        header_frame = tk.Frame(self.inner, bg='#0D1117')
        header_frame.pack(fill='x', pady=(0, 10))
        
        title = tk.Label(
            header_frame, text="🧠 SAVED SUGGESTIONS",
            font=("Consolas", 9, "bold"),
            fg='#4DFFB4', bg='#0D1117', anchor='w'
        )
        title.pack(side='left')
        
        close_btn = tk.Label(
            header_frame, text="✕",
            font=("Consolas", 10),
            fg='#888888', bg='#0D1117', cursor="hand2"
        )
        close_btn.pack(side='right')
        close_btn.bind("<Button-1>", lambda e: self.hide())
        close_btn.bind("<Enter>", lambda e: close_btn.config(fg='#FFFFFF'))
        close_btn.bind("<Leave>", lambda e: close_btn.config(fg='#888888'))
        
        # Container for history items
        self.list_frame = tk.Frame(self.inner, bg='#0D1117')
        self.list_frame.pack(fill='both', expand=True)
        
        self.items = []
        self.is_visible = False
        
        # Initial geometry (hidden off-screen)
        sw = self.window.winfo_screenwidth()
        self.width = 340
        self.start_x = sw + 20
        self.normal_x = sw - self.width - 24
        self.window.geometry(f"{self.width}x400+{self.start_x}+40")
        self.window.withdraw()

    def add_item(self, text):
        """Add a new suggestion to the top of the history list with feedback buttons."""
        # Create item wrapper
        item_frame = tk.Frame(self.list_frame, bg='#1A1F2B', padx=10, pady=8)
        item_frame.pack(fill='x', pady=(0, 8), before=self.list_frame.winfo_children()[0] if self.list_frame.winfo_children() else None)
        
        text_frame = tk.Frame(item_frame, bg='#1A1F2B')
        text_frame.pack(side='left', fill='x', expand=True)
        
        lbl = tk.Label(
            text_frame, text=text,
            font=("Segoe UI", 10),
            fg='#E2E8F0', bg='#1A1F2B',
            wraplength=250, justify='left', anchor='w'
        )
        lbl.pack(fill='x')
        
        # Feedback Buttons frame
        btn_frame = tk.Frame(item_frame, bg='#1A1F2B')
        btn_frame.pack(side='right', padx=(5, 0))
        
        def handle_feedback(score, btn_up, btn_down):
            try:
                from context_engine import record_feedback
                record_feedback(text, score)
                # Visual acknowledge
                btn_up.config(fg='#4DFFB4' if score > 0 else '#555555')
                btn_down.config(fg='#FF4D4D' if score < 0 else '#555555')
                # Disable further clicks on this item
                btn_up.unbind("<Button-1>")
                btn_down.unbind("<Button-1>")
                btn_up.config(cursor="arrow")
                btn_down.config(cursor="arrow")
            except Exception as e:
                print(f"Feedback error: {e}")

        up_btn = tk.Label(btn_frame, text="👍", font=("Segoe UI Emoji", 10), fg='#888888', bg='#1A1F2B', cursor="hand2")
        up_btn.pack(side='left', padx=2)
        
        down_btn = tk.Label(btn_frame, text="👎", font=("Segoe UI Emoji", 10), fg='#888888', bg='#1A1F2B', cursor="hand2")
        down_btn.pack(side='left', padx=2)
        
        def handle_up(e):
            handle_feedback(1, up_btn, down_btn)
            
        def handle_down(e):
            handle_feedback(-1, up_btn, down_btn)
            
        up_btn.bind("<Button-1>", handle_up)
        down_btn.bind("<Button-1>", handle_down)
        
        self.items.append(item_frame)
        
        # Keep maximum of 10 items
        if len(self.items) > 10:
            oldest = self.items.pop(0)
            oldest.destroy()
            
        self.show()

    def show(self):
        if self.is_visible: return
        self.is_visible = True
        self.window.deiconify()
        self._slide_in_step(0)
        
    def hide(self):
        if not self.is_visible: return
        self.is_visible = False
        self._slide_out_step(0, self.normal_x, self.start_x)

    def _slide_in_step(self, step):
        total_steps = 15
        if step <= total_steps:
            t = step / total_steps
            ease = 1.0 - (1.0 - t)**2
            current_x = self.start_x + (self.normal_x - self.start_x) * ease
            self.window.geometry(f"{self.width}x400+{int(current_x)}+40")
            self.window.after(12, self._slide_in_step, step + 1)
        else:
            self.window.geometry(f"{self.width}x400+{int(self.normal_x)}+40")

    def _slide_out_step(self, step, start_x, end_x):
        total_steps = 12
        if step <= total_steps:
            t = step / total_steps
            ease = t**2
            current_x = start_x + (end_x - start_x) * ease
            self.window.geometry(f"{int(self.width)}x400+{int(current_x)}+40")
            self.window.after(12, self._slide_out_step, step + 1, start_x, end_x)
        else:
            self.window.withdraw()


class PopupWindow:
    """Single popup window in the stack with glassmorphism aesthetic."""
    def __init__(self, parent_root, text, audio_text, on_dismiss):
        self.window = tk.Toplevel(parent_root)
        self.on_dismiss = on_dismiss
        self.parent_overlay = getattr(parent_root, 'ghost_overlay_ref', None)
        self.text = text
        self.audio_text = audio_text
        self._dismissed = False
        
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)
        self.window.attributes('-alpha', 0.92)  # Glass transparency
        self.window.configure(bg='#0D1117')
        
        # Border simulation (bright 1px frame)
        self.outer = tk.Frame(self.window, bg='#3A3A3A', padx=1, pady=1)
        self.outer.pack(fill='both', expand=True)
        
        self.inner = tk.Frame(self.outer, bg='#0D1117', padx=18, pady=14)
        self.inner.pack(fill='both', expand=True)
        
        # Header with neon glow effect via layered labels
        self.header_frame = tk.Frame(self.inner, bg='#0D1117', height=20)
        self.header_frame.pack(fill='x', pady=(0, 6))
        self.header_frame.pack_propagate(False)
        
        self.label_glow = tk.Label(
            self.header_frame, text="⚡ JARVIS",
            font=("Consolas", 9, "bold"),
            fg='#1F6648', bg='#0D1117', anchor='w'
        )
        self.label_glow.place(x=0, y=1, relwidth=1.0, relheight=1.0)
        
        self.label_header = tk.Label(
            self.header_frame, text="⚡ JARVIS",
            font=("Consolas", 9, "bold"),
            fg='#4DFFB4', bg='#0D1117', anchor='w'
        )
        self.label_header.place(x=0, y=0, relwidth=1.0, relheight=1.0)
        
        # Regenerate Button (only if audio_text is available)
        if self.audio_text:
            self.regen_btn = tk.Label(
                self.header_frame, text="⟲ REGENERATE",
                font=("Consolas", 8, "bold"),
                fg='#888888', bg='#0D1117', cursor="hand2"
            )
            self.regen_btn.pack(side='right')
            self.regen_btn.bind("<Button-1>", lambda e: self.on_regenerate())
            self.regen_btn.bind("<Enter>", lambda e: self.regen_btn.config(fg='#FFFFFF'))
            self.regen_btn.bind("<Leave>", lambda e: self.regen_btn.config(fg='#888888'))
        
        options = [opt.strip() for opt in text.split('|') if opt.strip()]
        self.is_multichoice = len(options) > 1
        
        if self.is_multichoice:
            self.label_text = tk.Label(
                self.inner, text="Multiple options found. Choose one:",
                font=("Segoe UI", 10, "italic"),
                fg='#A0A0A0', bg='#0D1117',
                wraplength=340, justify='left', anchor='w'
            )
            self.label_text.pack(fill='x', pady=(0, 4))
            
            for opt in options:
                btn_frame = tk.Frame(self.inner, bg='#1C222F')
                btn_frame.pack(fill='x', pady=3)
                
                btn_lbl = tk.Label(
                    btn_frame, text=opt,
                    font=("Segoe UI", 11), fg='#FFFFFF', bg='#1C222F',
                    wraplength=320, justify='left', anchor='w', cursor="hand2",
                    padx=6, pady=4
                )
                btn_lbl.pack(fill='x')
                
                def make_click_proxy(val):
                    return lambda e: self.on_option_pick(val)
                    
                def make_enter_proxy(f, l):
                    return lambda e: (f.config(bg='#2D3748'), l.config(bg='#2D3748'))
                    
                def make_leave_proxy(f, l):
                    return lambda e: (f.config(bg='#1C222F'), l.config(bg='#1C222F'))
                
                for w in (btn_frame, btn_lbl):
                    w.bind("<Button-1>", make_click_proxy(opt))
                    w.bind("<Enter>", make_enter_proxy(btn_frame, btn_lbl))
                    w.bind("<Leave>", make_leave_proxy(btn_frame, btn_lbl))
            
            for w in (self.window, self.outer, self.inner, self.header_frame, self.label_glow, self.label_header, self.label_text):
                w.bind("<Button-1>", lambda e: self.dismiss())
        else:
            self.label_text = tk.Label(
                self.inner, text=text,
                font=("Segoe UI", 11),
                fg='#FFFFFF', bg='#0D1117',
                wraplength=340, justify='left', anchor='w'
            )
            self.label_text.pack(fill='x')
            
            # Bind click to dismiss/save everywhere
            for w in (self.window, self.outer, self.inner, self.header_frame, self.label_glow, self.label_header, self.label_text):
                w.bind("<Button-1>", lambda e: self.on_click())
                w.config(cursor="hand2")
            
        # Initial hidden setup to calculate height
        sw = self.window.winfo_screenwidth()
        sh = self.window.winfo_screenheight()
        self.window.geometry(f"380x80+{sw+100}+{sh+100}")
        self.window.update_idletasks()
        
        self.width = max(self.window.winfo_reqwidth(), 380)
        self.height = max(self.window.winfo_reqheight(), 80)
        
        self.target_y: float | None = None
        self.current_y: float | None = None
        
        self.normal_x: float = sw - self.width - 24
        self.start_x: float = sw + 20
        self.current_x: float = self.start_x
        
        self._slide_after_id: str | None = None
        self._shift_after_id: str | None = None
        self._hold_after_id: str | None = None

    def _calculate_hold_ms(self, text: str) -> int:
        """Calculate display time based on message length."""
        word_count = len(text.split())
        if word_count <= 8:
            return 3000   # Short — 3 seconds
        elif word_count <= 14:
            return 5000   # Medium — 5 seconds
        elif word_count <= 20:
            return 7000   # Long — 7 seconds
        else:
            return 9000   # Very long — 9 seconds

    def setup_geometry(self, initial_target_y):
        self.target_y = float(initial_target_y)
        self.current_y = float(initial_target_y)
        self.window.geometry(f"{int(self.width)}x{int(self.height)}+{int(self.current_x)}+{int(self.current_y)}")

    def start_slide_in(self):
        self._slide_in_step(0)
    
    def _calculate_hold_ms(self, text: str) -> int:
        """Adaptive display time based on word count."""
        word_count = len(text.split())
        if word_count <= 8:
            return 3000
        elif word_count <= 14:
            return 5000
        elif word_count <= 20:
            return 7000
        else:
            return 9000 
        
    def _slide_in_step(self, step):
        if self._dismissed: return
        total_steps = 20
        if step <= total_steps:
            t = step / total_steps
            ease = 1.0 - (1.0 - t)**2  # ease-out
            self.current_x = float(self.start_x + (self.normal_x - self.start_x) * ease)
            # Ensure float->int cast for geometry
            _y = int(self.current_y) if self.current_y is not None else 0
            self.window.geometry(f"{int(self.width)}x{int(self.height)}+{int(self.current_x)}+{_y}")
            def slide_callback(step_val=step + 1):
                self._slide_in_step(step_val)
            self._slide_after_id = self.window.after(12, slide_callback) # type: ignore
        else:
            self.current_x = float(self.normal_x)
            _y = int(self.current_y) if self.current_y is not None else 0
            self.window.geometry(f"{int(self.width)}x{int(self.height)}+{int(self.current_x)}+{_y}")
            hold_ms = self._calculate_hold_ms(self.text)
            self._hold_after_id = self.window.after(hold_ms, self.dismiss)

    def animate_to_y(self, new_y):
        if self._dismissed: return
        if self._shift_after_id:
            self.window.after_cancel(self._shift_after_id)
            self._shift_after_id = None
            
        self.target_y = new_y
        self._shift_step(0, self.current_y, self.target_y)
        
    def _shift_step(self, step, start_y, end_y):
        if self._dismissed: return
        total_steps = 15
        if step <= total_steps:
            t = step / total_steps
            ease = 1.0 - (1.0 - t)**2  # ease-out
            self.current_y = float(start_y + (end_y - start_y) * ease)
            self.window.geometry(f"{int(self.width)}x{int(self.height)}+{int(self.current_x)}+{int(self.current_y)}")
            def shift_callback(step_val=step + 1, sy=start_y, ey=end_y):
                self._shift_step(step_val, sy, ey)
            self._shift_after_id = self.window.after(16, shift_callback) # type: ignore
        else:
            self.current_y = float(end_y)
            self.window.geometry(f"{int(self.width)}x{int(self.height)}+{int(self.current_x)}+{int(self.current_y)}")

    def on_option_pick(self, chosen_text):
        """Handle user selecting one of the multiple options."""
        if self._dismissed: return
        self.text = chosen_text
        self.is_multichoice = False
        
        # Destroy everything below header
        for child in self.inner.winfo_children():
            if child != self.header_frame:
                child.destroy()
                
        # Show final choice
        self.label_text = tk.Label(
            self.inner, text=self.text,
            font=("Segoe UI", 11),
            fg='#FFFFFF', bg='#0D1117',
            wraplength=340, justify='left', anchor='w'
        )
        self.label_text.pack(fill='x', pady=(6,0))
        
        # Rebind to allow saving to history
        for w in (self.window, self.outer, self.inner, self.header_frame, self.label_glow, self.label_header, self.label_text):
            w.bind("<Button-1>", lambda e: self.on_click())
            w.config(cursor="hand2")
            
        # Recalculate size and position
        self.window.update_idletasks()
        old_height = self.height
        self.height = max(self.window.winfo_reqheight(), 80)
        _y = int(self.current_y) if self.current_y is not None else 0
        self.window.geometry(f"{int(self.width)}x{int(self.height)}+{int(self.current_x)}+{_y}")
        
        if self.height != old_height and self.parent_overlay:
            self.parent_overlay._recalculate_stack()
            
        # Reset hold timer for final choice
        if self._hold_after_id is not None:
            self.window.after_cancel(self._hold_after_id)
        hold_ms = self._calculate_hold_ms(self.text)
        self._hold_after_id = self.window.after(max(hold_ms, 4000), self.dismiss)

    def on_click(self):
        """When clicked, dismiss the popup but save to history panel."""
        if self._dismissed: return
        # Ignore clicks if we're in multi-choice mode (must pick a button)
        if hasattr(self, 'is_multichoice') and self.is_multichoice:
            return
            
        if self.parent_overlay and hasattr(self.parent_overlay, 'history_panel'):
            self.parent_overlay.history_panel.add_item(self.text)
        self.dismiss()

    def on_regenerate(self):
        """Request a new LLM generation with higher temperature."""
        if self._dismissed or not self.audio_text: return
        
        import threading
        
        # UI state: loading
        if hasattr(self, 'regen_btn'):
            self.regen_btn.config(text="⟲ ...", fg="#E8FF47")
            self.regen_btn.unbind("<Button-1>")
            
        if self._hold_after_id is not None:
            self.window.after_cancel(self._hold_after_id)
            self._hold_after_id = None
            
        def fetch_new_suggestion():
            try:
                # Lazy import to avoid circular dependencies
                from context_engine import get_suggestion
                new_text = get_suggestion(self.audio_text, None, regenerate=True)
                
                # Update UI safely in main thread
                self.window.after(0, lambda: self._apply_regeneration(new_text))
                
            except Exception as e:
                print(f"Regenerate failed: {e}")
                self.window.after(0, lambda: self.dismiss())
                
        threading.Thread(target=fetch_new_suggestion, daemon=True).start()
        
    def _apply_regeneration(self, new_text):
        if self._dismissed: return
        
        if new_text == "SILENT":
            self.dismiss()
            return
            
        # Treat as option pick internally to reuse the UI rebuilding logic
        self.on_option_pick(new_text)
        
        # Reset regen button state
        if hasattr(self, 'regen_btn') and self.regen_btn.winfo_exists():
            self.regen_btn.config(text="⟲ REGENERATE", fg='#888888')
            self.regen_btn.bind("<Button-1>", lambda e: self.on_regenerate())

    def dismiss(self, event=None):
        if self._dismissed: return
        self._dismissed = True
        if self._hold_after_id is not None:
            self.window.after_cancel(self._hold_after_id)
        if self._slide_after_id is not None:
            self.window.after_cancel(self._slide_after_id)
        if self._shift_after_id is not None:
            self.window.after_cancel(self._shift_after_id)
            
        self.on_dismiss(self)
        self._slide_out_step(0, self.current_x, self.start_x)
        
    def _slide_out_step(self, step, start_x, end_x):
        total_steps = 15
        if step <= total_steps:
            t = step / total_steps
            ease = t**2  # ease-in
            self.current_x = float(start_x + (end_x - start_x) * ease)
            _y = int(self.current_y) if self.current_y is not None else 0
            self.window.geometry(f"{int(self.width)}x{int(self.height)}+{int(self.current_x)}+{_y}")
            def slide_out_callback(step_val=step + 1, sx=start_x, ex=end_x):
                self._slide_out_step(step_val, sx, ex)
            self.window.after(13, slide_out_callback) # type: ignore
        else:
            self.window.withdraw()
            self.window.destroy()


class GhostOverlay:
    """Manages the popup stack and UI orchestration as invisible root."""
    def __init__(self, root):
        self.root = root
        self.root.ghost_overlay_ref = self  # Give children access to overlay manager
        self.root.withdraw()
        self._popup_stack = []
        self._popup_queue = queue.Queue()
        self.MAX_STACK = 3
        self.STACK_GAP = 12
        
        self.history_panel = HistoryPanel(root)
        
        self._poll_queue()
        
    def get_hwnd(self):
        """Expose root window handle for screen capture exclusion."""
        try:
            return self.root.winfo_id()
        except (ImportError, AttributeError):
            pass # Windows-only fallbacke

    def show_popup(self, text, audio_text=None):
        """Thread-safe method to queue a popup message."""
        self._popup_queue.put((text, audio_text))
        
    def _poll_queue(self):
        try:
            item = self._popup_queue.get_nowait()
            if len(item) == 2 and isinstance(item, tuple):
                text_val = str(item[0])
                audio_val = str(item[1]) if item[1] is not None else None
                self._add_to_stack(text_val, audio_val)
            else:
                self._add_to_stack(str(item), None)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)
        
    def _add_to_stack(self, text, audio_text=None):
        # If stack is full, dismiss the oldest popup (first in list)
        if len(self._popup_stack) >= self.MAX_STACK:
            self._popup_stack[0].dismiss()
            
        popup = PopupWindow(self.root, text, audio_text, self._on_popup_dismiss)
        self._popup_stack.append(popup)
        self._recalculate_stack()
        popup.start_slide_in()
        
    def _recalculate_stack(self):
        """Shifts existing popups UP, mapping new ones at the bottom."""
        y_base = self.root.winfo_screenheight() - 60
        current_y = y_base
        
        # Iterate from newest to oldest
        for popup in reversed(self._popup_stack):
            current_y -= popup.height
            
            if popup.current_y is None:
                # newly created popup
                popup.setup_geometry(current_y)
            elif popup.target_y != current_y:
                # existing popup that needs to shift up
                popup.animate_to_y(current_y)
                
            current_y -= self.STACK_GAP
            
    def _on_popup_dismiss(self, popup):
        """Fires when a popup is dismissed, allowing remaining popups to shift down."""
        if popup in self._popup_stack:
            self._popup_stack.remove(popup)
            self._recalculate_stack()
