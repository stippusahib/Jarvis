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
        item_frame.pack(fill='x', pady=(0, 8))
        
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
        
        # Window affinity — invisible to screen sharing (Windows 11)
        try:
            import ctypes
            # WDA_EXCLUDEFROMCAPTURE = 0x00000011
            # This makes window invisible to all screen capture tools
            hwnd = self.window.winfo_id()
            ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0x00000011)  # type: ignore
        except Exception:
            pass  # Silently continue if not supported
        
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

        # Detect if this is a code context response (contains ISSUE: and FIX:)
        self.is_code_response = "ISSUE:" in text and "FIX:" in text
        self.copy_btn = None

        if self.is_code_response:
            # Parse ISSUE and FIX parts
            issue_text = ""
            fix_text = ""
            try:
                if "ISSUE:" in text:
                    issue_part = text.split("ISSUE:")[1]
                    if "FIX:" in issue_part:
                        issue_text = issue_part.split("FIX:")[0].strip()
                        fix_text = issue_part.split("FIX:")[1].strip()
                    else:
                        issue_text = issue_part.strip()
                else:
                    fix_text = text
            except Exception:
                fix_text = text

            # Update main label to show issue only
            if issue_text:
                self.label_text.config(
                    text=f"⚠️ {issue_text}",
                    fg='#FF6B6B',  # red for issue
                    font=("Consolas", 10)
                )

            # Code fix frame
            if fix_text:
                fix_frame = tk.Frame(self.inner, bg='#161B22', padx=8, pady=6)
                fix_frame.pack(fill='x', pady=(6, 0))

                # Fix label
                fix_label = tk.Label(
                    fix_frame,
                    text=fix_text,
                    font=("Consolas", 10),
                    fg='#4DFFB4',
                    bg='#161B22',
                    wraplength=300,
                    justify='left',
                    anchor='w'
                )
                fix_label.pack(fill='x', side='left', expand=True)

                # Copy button
                self.copy_btn = tk.Button(
                    fix_frame,
                    text="⎘",
                    font=("Consolas", 11, "bold"),
                    fg='#4DFFB4',
                    bg='#0D1117',
                    activebackground='#1C2128',
                    activeforeground='#FFFFFF',
                    relief='flat',
                    cursor='hand2',
                    bd=0,
                    padx=6,
                    command=lambda: self._copy_to_clipboard(fix_text)
                )
                self.copy_btn.pack(side='right', padx=(4, 0))

                # Bind click events to fix frame too
                for w in (fix_frame, fix_label):
                    w.bind("<Button-1>", lambda e: self.on_click())

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

    def _copy_to_clipboard(self, text: str):
        """Copy text to clipboard and show brief confirmation."""
        try:
            self.window.clipboard_clear()
            self.window.clipboard_append(text)
            self.window.update()
            # Flash copy button green briefly
            if self.copy_btn:
                self.copy_btn.config(text="✓", fg='#00FF88')
                self.window.after(1000, lambda: self.copy_btn.config(text="⎘", fg='#4DFFB4') if self.copy_btn else None)
            print(f"📋 Copied to clipboard: {text[:50]}...")
        except Exception as e:
            print(f"⚠️  Clipboard error: {e}")

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

    def setup_geometry(self, initial_target_y):
        self.target_y = float(initial_target_y)
        self.current_y = float(initial_target_y)
        self.window.geometry(f"{int(self.width)}x{int(self.height)}+{int(self.current_x)}+{int(self.current_y)}")

    def start_slide_in(self):
        self._slide_in_step(0)
        
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
            self._slide_after_id = self.window.after(12, slide_callback)  # type: ignore
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
            self._shift_after_id = self.window.after(16, shift_callback)  # type: ignore
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
        """When clicked — save to history AND open chat panel."""
        if self._dismissed: return
        if hasattr(self, 'is_multichoice') and self.is_multichoice:
            return

        # Save to history
        try:
            if self.parent_overlay and hasattr(self.parent_overlay, 'history_panel'):
                self.parent_overlay.history_panel.add_item(self.text)
        except Exception:
            pass

        # Open chat panel if not already open
        try:
            if self.parent_overlay and not self.parent_overlay.chat_panel_open:
                # Calculate position below this popup
                popup_x = int(self.current_x) if self.current_x else 0
                popup_bottom_y = int(self.current_y + self.height) if self.current_y else 0
                
                self.parent_overlay.open_chat(
                    self.text,
                    popup_x,
                    popup_bottom_y
                )
                return  # Don't dismiss — keep popup visible during chat
        except Exception:
            pass

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
            self.window.after(13, slide_out_callback)  # type: ignore
        else:
            self.window.withdraw()
            self.window.destroy()


class ChatPanel:
    """Inline chat panel that appears below a popup when clicked."""
    
    MAX_MESSAGES = 5  # per session limit
    INACTIVITY_TIMEOUT = 30000  # 30 seconds in ms
    
    def __init__(self, parent_root, initial_suggestion, on_close):
        self.window = tk.Toplevel(parent_root)
        self.on_close = on_close
        self.message_count = 0
        self.chat_history = []  # RAM only — never stored
        self._inactivity_timer = None
        self._closed = False
        
        # Window affinity — invisible to screen share
        try:
            import ctypes
            hwnd = self.window.winfo_id()
            ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0x00000011)
        except Exception:
            pass
        
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)
        self.window.attributes('-alpha', 0.95)
        self.window.configure(bg='#0A0F1A')
        
        # Outer border
        outer = tk.Frame(self.window, bg='#2A3A4A', padx=1, pady=1)
        outer.pack(fill='both', expand=True)
        
        inner = tk.Frame(outer, bg='#0A0F1A', padx=0, pady=0)
        inner.pack(fill='both', expand=True)
        
        # Header
        self.header = tk.Label(
            inner,
            text=f"💬 CHAT  ({self.MAX_MESSAGES}/5 messages left)",
            font=("Consolas", 9, "bold"),
            fg='#4DFFB4', bg='#0A0F1A',
            anchor='w', padx=12, pady=6
        )
        self.header.pack(fill='x')
        
        # Separator
        tk.Frame(inner, bg='#2A3A4A', height=1).pack(fill='x')
        
        # Chat history — scrollable text area
        self.chat_frame = tk.Frame(inner, bg='#0A0F1A')
        self.chat_frame.pack(fill='both', expand=True, padx=8, pady=6)
        
        self.chat_text = tk.Text(
            self.chat_frame,
            font=("Consolas", 10),
            bg='#0A0F1A',
            fg='#FFFFFF',
            relief='flat',
            bd=0,
            wrap='word',
            height=6,
            width=40,
            state='disabled',
            cursor='arrow'
        )
        self.chat_text.pack(fill='both', expand=True)
        
        # Configure text tags for colors
        self.chat_text.tag_configure('jarvis', foreground='#4DFFB4', font=("Consolas", 10, "bold"))
        self.chat_text.tag_configure('user', foreground='#FFFFFF', font=("Consolas", 10))
        self.chat_text.tag_configure('system', foreground='#888888', font=("Consolas", 9, "italic"))
        
        # Separator
        tk.Frame(inner, bg='#2A3A4A', height=1).pack(fill='x')
        
        # Input row
        input_frame = tk.Frame(inner, bg='#0A0F1A', padx=8, pady=6)
        input_frame.pack(fill='x')
        
        self.input_var = tk.StringVar()
        self.input_field = tk.Entry(
            input_frame,
            textvariable=self.input_var,
            font=("Consolas", 10),
            bg='#161B22',
            fg='#FFFFFF',
            insertbackground='#4DFFB4',
            relief='flat',
            bd=4
        )
        self.input_field.pack(side='left', fill='x', expand=True, ipady=4)
        self.input_field.insert(0, "Ask JARVIS...")
        self.input_field.bind("<FocusIn>", self._clear_placeholder)
        self.input_field.bind("<FocusOut>", self._restore_placeholder)
        self.input_field.bind("<Return>", lambda e: self._send_message())
        
        self.send_btn = tk.Button(
            input_frame,
            text="▶",
            font=("Consolas", 11, "bold"),
            fg='#4DFFB4',
            bg='#0D1117',
            activebackground='#1C2128',
            activeforeground='#FFFFFF',
            relief='flat',
            bd=0,
            padx=8,
            cursor='hand2',
            command=self._send_message
        )
        self.send_btn.pack(side='right', padx=(4, 0))
        
        # Add initial suggestion as first JARVIS message
        self._add_message("JARVIS", initial_suggestion)
        
        # Window geometry — will be set by position_below()
        self.width = 380
        self.height = 220
        self.window.geometry(f"{self.width}x{self.height}+9999+9999")
        self.window.update_idletasks()
        self.height = max(self.window.winfo_reqheight(), 220)
        
        # Start inactivity timer
        self._reset_inactivity_timer()
        
        # Focus input
        self.window.after(100, lambda: self.input_field.focus_set())

    def position_below(self, popup_x, popup_bottom_y):
        """Position chat panel directly below the popup."""
        x = popup_x
        y = popup_bottom_y + 4  # 4px gap
        
        # Make sure it doesn't go off screen bottom
        sh = self.window.winfo_screenheight()
        if y + self.height > sh - 20:
            y = popup_bottom_y - self.height - 4  # above popup instead
        
        self.window.geometry(f"{self.width}x{self.height}+{int(x)}+{int(y)}")
        self.window.deiconify()

    def _clear_placeholder(self, event):
        if self.input_var.get() == "Ask JARVIS...":
            self.input_field.delete(0, 'end')
            self.input_field.config(fg='#FFFFFF')

    def _restore_placeholder(self, event):
        if not self.input_var.get():
            self.input_field.insert(0, "Ask JARVIS...")
            self.input_field.config(fg='#555555')

    def _add_message(self, sender: str, message: str):
        """Add a message to the chat history display."""
        self.chat_text.config(state='normal')
        
        if sender == "JARVIS":
            self.chat_text.insert('end', f"⚡ JARVIS: ", 'jarvis')
            self.chat_text.insert('end', f"{message}\n\n", 'jarvis')
        elif sender == "You":
            self.chat_text.insert('end', f"You: ", 'user')
            self.chat_text.insert('end', f"{message}\n\n", 'user')
        else:
            self.chat_text.insert('end', f"{message}\n", 'system')
        
        self.chat_text.config(state='disabled')
        self.chat_text.see('end')  # auto-scroll to bottom
        
        # Store in RAM history
        self.chat_history.append({"role": sender, "content": message})

    def _send_message(self):
        """Handle user sending a message."""
        if self._closed:
            return
            
        user_text = self.input_var.get().strip()
        if not user_text or user_text == "Ask JARVIS...":
            return
        
        # Check message limit
        if self.message_count >= self.MAX_MESSAGES:
            self._add_message("system", "⚠️ Chat limit reached (5/5). Start a new session.")
            return
        
        self.message_count += 1
        remaining = self.MAX_MESSAGES - self.message_count
        
        # Update header
        color = '#FF6B6B' if remaining <= 1 else '#4DFFB4'
        self.header.config(
            text=f"💬 CHAT  ({remaining}/5 messages left)",
            fg=color
        )
        
        # Clear input
        self.input_var.set("")
        self.input_field.config(fg='#FFFFFF')
        
        # Add user message
        self._add_message("You", user_text)
        
        # Disable input while processing
        self.input_field.config(state='disabled')
        self.send_btn.config(state='disabled', text="...")
        
        # Reset inactivity timer
        self._reset_inactivity_timer()
        
        # Get response in background thread
        import threading
        threading.Thread(
            target=self._fetch_response,
            args=(user_text,),
            daemon=True
        ).start()

    def _fetch_response(self, user_text: str):
        """Fetch JARVIS response in background thread."""
        try:
            from context_engine import get_suggestion
            
            # Build context from chat history for better responses
            context_text = user_text
            if len(self.chat_history) > 1:
                # Include last 2 exchanges for context
                recent = self.chat_history[-4:] if len(self.chat_history) >= 4 else self.chat_history
                context_parts = []
                for msg in recent[:-1]:  # exclude current message
                    context_parts.append(f"{msg['role']}: {msg['content']}")
                context_text = "\n".join(context_parts) + f"\nUser follow-up: {user_text}"
            
            response = get_suggestion(context_text, None, regenerate=False)
            
            if response == "SILENT":
                response = "I don't have anything specific to add on that."
            
            # Update UI in main thread
            self.window.after(0, lambda: self._display_response(response))
            
        except Exception as e:
            error_msg = "Something went wrong — try again."
            self.window.after(0, lambda: self._display_response(error_msg))

    def _display_response(self, response: str):
        """Display JARVIS response and re-enable input."""
        if self._closed:
            return
            
        self._add_message("JARVIS", response)
        
        # Re-enable input if limit not reached
        if self.message_count < self.MAX_MESSAGES:
            self.input_field.config(state='normal')
            self.send_btn.config(state='normal', text="▶")
            self.input_field.focus_set()
        else:
            self.input_field.config(state='disabled')
            self.send_btn.config(state='disabled', text="✓")
            self._add_message("system", "Chat limit reached. Session ended.")

    def _reset_inactivity_timer(self):
        """Reset the 30-second inactivity auto-close timer."""
        if self._inactivity_timer:
            try:
                self.window.after_cancel(self._inactivity_timer)
            except Exception:
                pass
        self._inactivity_timer = self.window.after(
            self.INACTIVITY_TIMEOUT,
            self.close
        )

    def close(self):
        """Close and destroy the chat panel."""
        if self._closed:
            return
        self._closed = True
        
        # Wipe chat history from RAM
        self.chat_history.clear()
        
        if self._inactivity_timer:
            try:
                self.window.after_cancel(self._inactivity_timer)
            except Exception:
                pass
        
        try:
            self.window.destroy()
        except Exception:
            pass
        
        # Notify parent
        if self.on_close:
            try:
                self.on_close()
            except Exception:
                pass


class GhostOverlay:
    """Manages the popup stack and UI orchestration as invisible root."""
    def __init__(self, root):
        self.root = root
        self.root.ghost_overlay_ref = self  # Give children access to overlay manager
        self.root.withdraw()
        
        # Apply window affinity to root too
        try:
            import ctypes
            hwnd = self.root.winfo_id()
            ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0x00000011)  # type: ignore
        except Exception:
            pass
        
        self._popup_stack = []
        self._popup_queue = queue.Queue()
        self.MAX_STACK = 3
        self.STACK_GAP = 12
        
        self.history_panel = HistoryPanel(root)
        self.chat_panel_open = False
        self._active_chat = None
        
        self._poll_queue()
        
    def get_hwnd(self):
        """Expose root window handle for screen capture exclusion."""
        try:
            return self.root.winfo_id()
        except (ImportError, AttributeError):
            pass  # Windows-only fallback

    def open_chat(self, initial_suggestion: str, popup_x: int, popup_bottom_y: int):
        """Open inline chat panel below the popup."""
        if self.chat_panel_open:
            return  # Only one chat at a time
        
        self.chat_panel_open = True
        
        def on_chat_close():
            self.chat_panel_open = False
            self._active_chat = None
        
        chat = ChatPanel(
            self.root,
            initial_suggestion,
            on_chat_close
        )
        chat.position_below(popup_x, popup_bottom_y)
        self._active_chat = chat

    def close_chat(self):
        """Close active chat if open."""
        if self._active_chat:
            self._active_chat.close()

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
