# JARVIS Dashboard — Premium dark-themed GUI using CustomTkinter.
# PRIVACY: Uses settings_manager.py for the ONLY disk writes (settings.json).
import customtkinter as ctk
from tkinter import filedialog
import tkinter as tk
import threading
import sys
import os
import pathlib

import settings_manager

# ── DPI Awareness (Windows) — crisp rendering ────────────────────
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

# Theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# Icon path
ICON_PATH = pathlib.Path(__file__).parent / "jarvis_icon.png"


class JarvisDashboard:
    """Premium control panel for JARVIS."""

    # ── Palette ───────────────────────────────────────────────────
    BG_DEEP     = '#060B14'
    BG          = '#0C1220'
    CARD        = '#111827'
    INPUT       = '#1A2332'
    BORDER      = '#1E293B'
    ACCENT      = '#4DFFB4'
    ACCENT_DARK = '#1B7A4E'
    ACCENT_GLOW = '#2AF598'
    TEXT        = '#F1F5F9'
    TEXT_SEC    = '#94A3B8'
    DIM         = '#64748B'
    RED         = '#EF4444'
    RED_DARK    = '#B91C1C'
    ORANGE      = '#F59E0B'
    GREEN_SOFT  = '#22C55E'

    def __init__(self):
        self.app = ctk.CTk()
        self.app.title('JARVIS')
        self.app.configure(fg_color=self.BG_DEEP)
        self.app.resizable(False, False)

        # Window icon
        try:
            if ICON_PATH.exists():
                icon_img = tk.PhotoImage(file=str(ICON_PATH))
                self.app.iconphoto(True, icon_img)
                self._icon_ref = icon_img  # prevent GC
        except Exception:
            pass

        # Size & center
        w, h = 480, 740
        x = (self.app.winfo_screenwidth() - w) // 2
        y = (self.app.winfo_screenheight() - h) // 2
        self.app.geometry(f'{w}x{h}+{x}+{y}')

        # State
        self._engine_running = False
        self._stop_event = threading.Event()
        self._settings = settings_manager.load_settings()
        self._overlay = None
        self._ghost_root = None
        self._pulse_after = None

        self._build_ui()
        self._load_fields()

    # ══════════════════════════════════════════════════════════════
    #  UI
    # ══════════════════════════════════════════════════════════════

    def _build_ui(self):

        # ─── Top Status Bar ──────────────────────────────
        top = ctk.CTkFrame(self.app, fg_color=self.BG, corner_radius=0, height=52)
        top.pack(fill='x')
        top.pack_propagate(False)

        # Title
        ctk.CTkLabel(
            top, text='  ⚡ JARVIS',
            font=ctk.CTkFont(family='Consolas', size=18, weight='bold'),
            text_color=self.ACCENT
        ).pack(side='left', padx=16)

        # Status indicator frame
        self._status_frame = ctk.CTkFrame(top, fg_color='transparent')
        self._status_frame.pack(side='right', padx=16)

        self._status_dot = ctk.CTkLabel(
            self._status_frame, text='●',
            font=ctk.CTkFont(size=14),
            text_color=self.RED
        )
        self._status_dot.pack(side='left', padx=(0, 6))

        self._status_text = ctk.CTkLabel(
            self._status_frame, text='Offline',
            font=ctk.CTkFont(family='Segoe UI', size=12),
            text_color=self.DIM
        )
        self._status_text.pack(side='left')

        # ─── Scrollable Content ──────────────────────────
        scroll = ctk.CTkScrollableFrame(
            self.app, fg_color=self.BG_DEEP,
            scrollbar_button_color=self.BORDER,
            scrollbar_button_hover_color=self.DIM
        )
        scroll.pack(fill='both', expand=True, padx=0, pady=0)

        # ─── Engine Control Card ─────────────────────────
        engine_card = ctk.CTkFrame(scroll, fg_color=self.CARD, corner_radius=14)
        engine_card.pack(fill='x', padx=20, pady=(16, 0))

        engine_inner = ctk.CTkFrame(engine_card, fg_color='transparent')
        engine_inner.pack(fill='x', padx=20, pady=18)

        ctk.CTkLabel(
            engine_inner, text='ENGINE',
            font=ctk.CTkFont(family='Consolas', size=10, weight='bold'),
            text_color=self.DIM
        ).pack(anchor='w')

        self._toggle_btn = ctk.CTkButton(
            engine_inner,
            text='▶   START JARVIS',
            font=ctk.CTkFont(family='Segoe UI', size=15, weight='bold'),
            fg_color=self.ACCENT,
            text_color=self.BG_DEEP,
            hover_color=self.ACCENT_DARK,
            corner_radius=10,
            height=50,
            command=self._toggle_engine
        )
        self._toggle_btn.pack(fill='x', pady=(10, 0))

        # Engine info row
        info_row = ctk.CTkFrame(engine_inner, fg_color='transparent')
        info_row.pack(fill='x', pady=(10, 0))

        self._engine_info = ctk.CTkLabel(
            info_row,
            text='🔑 Ctrl+Shift+J  •  🎤 Mic  •  👁️ Vision',
            font=ctk.CTkFont(family='Consolas', size=10),
            text_color=self.DIM
        )
        self._engine_info.pack(side='left')

        # ─── Profile Card ────────────────────────────────
        profile_card = ctk.CTkFrame(scroll, fg_color=self.CARD, corner_radius=14)
        profile_card.pack(fill='x', padx=20, pady=(12, 0))

        profile_inner = ctk.CTkFrame(profile_card, fg_color='transparent')
        profile_inner.pack(fill='x', padx=20, pady=18)

        ctk.CTkLabel(
            profile_inner, text='PROFILE',
            font=ctk.CTkFont(family='Consolas', size=10, weight='bold'),
            text_color=self.DIM
        ).pack(anchor='w')

        # Name
        ctk.CTkLabel(
            profile_inner, text='Your Name',
            font=ctk.CTkFont(size=12, weight='bold'), text_color=self.TEXT_SEC
        ).pack(anchor='w', pady=(12, 0))

        self._name_entry = ctk.CTkEntry(
            profile_inner, placeholder_text='e.g. Alfie',
            font=ctk.CTkFont(size=13),
            fg_color=self.INPUT, text_color=self.TEXT,
            border_color=self.BORDER, corner_radius=8, height=36
        )
        self._name_entry.pack(fill='x', pady=(4, 0))

        # Wake Words
        ctk.CTkLabel(
            profile_inner, text='Wake / Trigger Words',
            font=ctk.CTkFont(size=12, weight='bold'), text_color=self.TEXT_SEC
        ).pack(anchor='w', pady=(14, 0))
        ctk.CTkLabel(
            profile_inner, text='Comma separated — your name is auto-added',
            font=ctk.CTkFont(size=10), text_color=self.DIM
        ).pack(anchor='w')

        self._wake_entry = ctk.CTkEntry(
            profile_inner, placeholder_text='jarvis, hey jarvis, ok jarvis',
            font=ctk.CTkFont(size=13),
            fg_color=self.INPUT, text_color=self.TEXT,
            border_color=self.BORDER, corner_radius=8, height=36
        )
        self._wake_entry.pack(fill='x', pady=(4, 0))

        # Vision Keywords
        ctk.CTkLabel(
            profile_inner, text='Extra Vision Keywords',
            font=ctk.CTkFont(size=12, weight='bold'), text_color=self.TEXT_SEC
        ).pack(anchor='w', pady=(14, 0))
        ctk.CTkLabel(
            profile_inner, text='Comma separated — adds to screen-scan triggers',
            font=ctk.CTkFont(size=10), text_color=self.DIM
        ).pack(anchor='w')

        self._vision_entry = ctk.CTkEntry(
            profile_inner, placeholder_text='diagram, flowchart, ui',
            font=ctk.CTkFont(size=13),
            fg_color=self.INPUT, text_color=self.TEXT,
            border_color=self.BORDER, corner_radius=8, height=36
        )
        self._vision_entry.pack(fill='x', pady=(4, 0))

        # Save
        self._save_btn = ctk.CTkButton(
            profile_inner,
            text='💾   SAVE',
            font=ctk.CTkFont(size=13, weight='bold'),
            fg_color=self.INPUT, text_color=self.ACCENT,
            hover_color=self.BORDER, corner_radius=8, height=38,
            command=self._save_settings
        )
        self._save_btn.pack(fill='x', pady=(16, 0))

        # ─── Monitored Paths Card ────────────────────────
        paths_card = ctk.CTkFrame(scroll, fg_color=self.CARD, corner_radius=14)
        paths_card.pack(fill='x', padx=20, pady=(12, 0))

        paths_inner = ctk.CTkFrame(paths_card, fg_color='transparent')
        paths_inner.pack(fill='x', padx=20, pady=18)

        ctk.CTkLabel(
            paths_inner, text='MONITORED PATHS',
            font=ctk.CTkFont(family='Consolas', size=10, weight='bold'),
            text_color=self.DIM
        ).pack(anchor='w')

        ctk.CTkLabel(
            paths_inner,
            text='JARVIS watches these folders & files for context',
            font=ctk.CTkFont(size=10), text_color=self.DIM
        ).pack(anchor='w', pady=(2, 0))

        # Path list
        self._path_frame = ctk.CTkFrame(paths_inner, fg_color=self.INPUT, corner_radius=8)
        self._path_frame.pack(fill='x', pady=(10, 0))

        self._path_labels = []  # track labels for removal

        # Buttons
        btn_row = ctk.CTkFrame(paths_inner, fg_color='transparent')
        btn_row.pack(fill='x', pady=(10, 0))

        ctk.CTkButton(
            btn_row, text='📁 Folder', width=100,
            font=ctk.CTkFont(size=11),
            fg_color=self.INPUT, text_color=self.ACCENT,
            hover_color=self.BORDER, corner_radius=8, height=32,
            command=self._add_folder
        ).pack(side='left', padx=(0, 6))

        ctk.CTkButton(
            btn_row, text='📄 File', width=90,
            font=ctk.CTkFont(size=11),
            fg_color=self.INPUT, text_color=self.ACCENT,
            hover_color=self.BORDER, corner_radius=8, height=32,
            command=self._add_file
        ).pack(side='left', padx=(0, 6))

        ctk.CTkButton(
            btn_row, text='✕ Remove', width=100,
            font=ctk.CTkFont(size=11),
            fg_color=self.INPUT, text_color=self.RED,
            hover_color=self.BORDER, corner_radius=8, height=32,
            command=self._remove_last_path
        ).pack(side='right')

        # ─── Footer ──────────────────────────────────────
        footer = ctk.CTkFrame(scroll, fg_color='transparent')
        footer.pack(fill='x', padx=20, pady=(16, 16))

        ctk.CTkLabel(
            footer,
            text='100% Offline  •  Zero Cloud  •  RAM Only  •  Privacy First',
            font=ctk.CTkFont(family='Consolas', size=9),
            text_color='#334155'
        ).pack()

    # ══════════════════════════════════════════════════════════════
    #  SETTINGS I/O
    # ══════════════════════════════════════════════════════════════

    def _load_fields(self):
        s = self._settings
        name = s.get('user_name', '')
        if name:
            self._name_entry.insert(0, name)

        wake = s.get('wake_words', [])
        if wake:
            self._wake_entry.insert(0, ', '.join(wake))

        vision = s.get('vision_keywords', [])
        if vision:
            self._vision_entry.insert(0, ', '.join(vision))

        self._rebuild_path_list()

    def _rebuild_path_list(self):
        """Rebuild the visual path list from settings."""
        # Clear existing
        for lbl in self._path_labels:
            try:
                lbl.destroy()
            except Exception:
                pass
        self._path_labels.clear()

        paths = self._settings.get('custom_paths', [])

        if not paths:
            empty = ctk.CTkLabel(
                self._path_frame,
                text='  No paths configured — add folders or files above',
                font=ctk.CTkFont(family='Consolas', size=10),
                text_color=self.DIM,
                anchor='w'
            )
            empty.pack(fill='x', padx=10, pady=10)
            self._path_labels.append(empty)
            return

        for i, p in enumerate(paths):
            row = ctk.CTkFrame(self._path_frame, fg_color='transparent')
            row.pack(fill='x', padx=10, pady=(6 if i == 0 else 2, 6 if i == len(paths)-1 else 0))

            # Icon based on type
            icon = '📁' if os.path.isdir(p) else '📄'

            # Truncate long paths
            display = p
            if len(display) > 48:
                display = '...' + display[-45:]

            lbl = ctk.CTkLabel(
                row, text=f'{icon}  {display}',
                font=ctk.CTkFont(family='Consolas', size=11),
                text_color=self.TEXT_SEC, anchor='w'
            )
            lbl.pack(fill='x')
            self._path_labels.append(row)

    def _save_settings(self):
        name = self._name_entry.get().strip()
        wake_raw = self._wake_entry.get().strip()
        vision_raw = self._vision_entry.get().strip()

        wake_words = [w.strip().lower() for w in wake_raw.split(',') if w.strip()]
        vision_kw  = [w.strip().lower() for w in vision_raw.split(',') if w.strip()]

        if name and name.lower() not in wake_words:
            wake_words.append(name.lower())

        self._settings['user_name'] = name
        self._settings['wake_words'] = wake_words
        self._settings['vision_keywords'] = vision_kw
        settings_manager.save_settings(self._settings)

        # Flash
        self._save_btn.configure(text='✓  Saved!', fg_color=self.ACCENT_DARK, text_color=self.ACCENT_GLOW)
        self.app.after(1500, lambda: self._save_btn.configure(
            text='💾   SAVE', fg_color=self.INPUT, text_color=self.ACCENT
        ))

    # ══════════════════════════════════════════════════════════════
    #  PATH MANAGEMENT
    # ══════════════════════════════════════════════════════════════

    def _add_folder(self):
        path = filedialog.askdirectory(title='Select a folder for JARVIS to monitor')
        if path:
            paths = self._settings.get('custom_paths', [])
            if path not in paths:
                paths.append(path)
                self._settings['custom_paths'] = paths
                settings_manager.save_settings(self._settings)
                self._rebuild_path_list()

    def _add_file(self):
        path = filedialog.askopenfilename(title='Select a file for JARVIS to monitor')
        if path:
            paths = self._settings.get('custom_paths', [])
            if path not in paths:
                paths.append(path)
                self._settings['custom_paths'] = paths
                settings_manager.save_settings(self._settings)
                self._rebuild_path_list()

    def _remove_last_path(self):
        paths = self._settings.get('custom_paths', [])
        if paths:
            paths.pop()
            self._settings['custom_paths'] = paths
            settings_manager.save_settings(self._settings)
            self._rebuild_path_list()

    # ══════════════════════════════════════════════════════════════
    #  ENGINE CONTROL
    # ══════════════════════════════════════════════════════════════

    def _toggle_engine(self):
        if self._engine_running:
            self._stop_engine()
        else:
            self._start_engine()

    def _start_engine(self):
        self._stop_event.clear()
        self._engine_running = True

        self._toggle_btn.configure(
            text='■   STOP JARVIS',
            fg_color=self.RED,
            text_color=self.TEXT,
            hover_color=self.RED_DARK
        )
        self._status_text.configure(text='Online', text_color=self.ACCENT)
        self._status_dot.configure(text_color=self.ACCENT)
        self._start_pulse()

        # Separate hidden root for ghost overlay
        def _create_ghost():
            self._ghost_root = tk.Toplevel(self.app)
            self._ghost_root.withdraw()
        self.app.after(0, _create_ghost)

        self._engine_thread = threading.Thread(target=self._engine_worker, daemon=True)
        self._engine_thread.start()

    def _stop_engine(self):
        self._stop_event.set()
        self._engine_running = False
        self._stop_pulse()

        self._toggle_btn.configure(
            text='▶   START JARVIS',
            fg_color=self.ACCENT,
            text_color=self.BG_DEEP,
            hover_color=self.ACCENT_DARK
        )
        self._status_text.configure(text='Offline', text_color=self.DIM)
        self._status_dot.configure(text_color=self.RED)

        if self._ghost_root:
            try:
                self._ghost_root.destroy()
            except Exception:
                pass
            self._ghost_root = None
            self._overlay = None

    # ── Pulse animation for status dot ────────────────────────────

    def _start_pulse(self):
        self._pulse_step(0)

    def _pulse_step(self, step):
        if not self._engine_running:
            return
        colors = [self.ACCENT, self.ACCENT_GLOW, self.ACCENT, self.GREEN_SOFT]
        self._status_dot.configure(text_color=colors[step % len(colors)])
        self._pulse_after = self.app.after(600, lambda: self._pulse_step(step + 1))

    def _stop_pulse(self):
        if self._pulse_after:
            try:
                self.app.after_cancel(self._pulse_after)
            except Exception:
                pass
            self._pulse_after = None

    # ── Engine Worker ─────────────────────────────────────────────

    def _engine_worker(self):
        try:
            from context_engine import get_suggestion, prewarm_ollama
            from audio_listener import AudioListener
            from screen_reader import ScreenReader

            prewarm_ollama()

            # Wait for ghost root
            import time
            for _ in range(50):
                if self._ghost_root:
                    break
                time.sleep(0.1)

            # Create overlay on ghost root (main thread)
            overlay_ready = threading.Event()

            def _create_overlay():
                try:
                    from ghost_overlay import GhostOverlay
                    self._overlay = GhostOverlay(self._ghost_root)
                except Exception as e:
                    print(f'⚠️  Overlay failed: {e}')
                overlay_ready.set()

            self.app.after(0, _create_overlay)
            overlay_ready.wait(timeout=5)

            screen = ScreenReader()
            try:
                if self._overlay:
                    screen.set_overlay_hwnd(self._overlay.get_hwnd())
            except Exception:
                pass

            # Hotkey
            try:
                import keyboard
                def on_hotkey():
                    try:
                        sb = screen.get_latest()
                        if sb and self._overlay:
                            sug = get_suggestion(
                                "Analyze this screen carefully. Identify bugs, errors, or improvements.",
                                sb, force_vision=True
                            )
                            if sug and sug != 'SILENT':
                                self._overlay.show_popup(sug, "hotkey")
                    except Exception:
                        pass
                keyboard.add_hotkey('ctrl+shift+j', on_hotkey, suppress=False)
                print('🔑 Hotkey active: Ctrl+Shift+J')
            except Exception:
                pass

            audio = AudioListener()
            audio.start()
            screen.start()
            screen.interval = 4
            print('🧠 JARVIS engine started from GUI')

            while not self._stop_event.is_set():
                try:
                    audio_text = audio.output_queue.get(timeout=1)
                    if audio_text:
                        print(f'🎤 Heard: {audio_text[:80]}')
                        screen_b64 = screen.get_latest()
                        suggestion = get_suggestion(audio_text, screen_b64)
                        if suggestion != 'SILENT' and self._overlay:
                            print(f'⚡ Suggestion: {suggestion}')
                            self._overlay.show_popup(suggestion, audio_text)
                        else:
                            print('   (SILENT)')
                except Exception:
                    continue

            audio.stop()
            screen.stop()
            print('🧠 JARVIS engine stopped')

        except Exception as e:
            print(f'⚠️  Engine error: {e}')
            self.app.after(0, self._stop_engine)

    # ══════════════════════════════════════════════════════════════
    #  LIFECYCLE
    # ══════════════════════════════════════════════════════════════

    def run(self):
        self.app.protocol('WM_DELETE_WINDOW', self._on_close)
        self.app.mainloop()

    def _on_close(self):
        if self._engine_running:
            self._stop_engine()
        self.app.destroy()
        sys.exit(0)


def launch():
    app = JarvisDashboard()
    app.run()


if __name__ == '__main__':
    launch()
