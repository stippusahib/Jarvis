# JARVIS Dashboard — Premium dark-themed GUI using CustomTkinter.
# PRIVACY: Uses settings_manager.py for the ONLY disk writes (settings.json).
import customtkinter as ctk
from tkinter import filedialog
import tkinter as tk
import threading
import sys
import os

import settings_manager

# ── DPI Awareness (Windows) — crisp rendering ────────────────────
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor DPI aware
except Exception:
    pass

# Theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class JarvisDashboard:
    """Premium control panel for JARVIS."""

    # ── Palette ───────────────────────────────────────────────────
    BG          = '#0A0F1A'
    CARD        = '#0D1117'
    INPUT       = '#161B22'
    BORDER      = '#1C2128'
    ACCENT      = '#4DFFB4'
    ACCENT_DARK = '#1F6648'
    TEXT        = '#E6EDF3'
    DIM         = '#7D8590'
    RED         = '#FF6B6B'
    ORANGE      = '#FFB347'

    def __init__(self):
        self.app = ctk.CTk()
        self.app.title('JARVIS — Control Panel')
        self.app.configure(fg_color=self.BG)
        self.app.resizable(False, False)

        # Center on screen
        w, h = 560, 720
        x = (self.app.winfo_screenwidth() - w) // 2
        y = (self.app.winfo_screenheight() - h) // 2
        self.app.geometry(f'{w}x{h}+{x}+{y}')

        # State
        self._engine_running = False
        self._stop_event = threading.Event()
        self._settings = settings_manager.load_settings()
        self._overlay = None
        self._ghost_root = None

        self._build_ui()
        self._load_fields()

    # ══════════════════════════════════════════════════════════════
    #  UI CONSTRUCTION
    # ══════════════════════════════════════════════════════════════

    def _build_ui(self):
        # ─── Header ──────────────────────────────────────
        header = ctk.CTkFrame(self.app, fg_color=self.BG, height=60)
        header.pack(fill='x', padx=28, pady=(20, 0))
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text='⚡  JARVIS',
            font=ctk.CTkFont(family='Segoe UI', size=26, weight='bold'),
            text_color=self.ACCENT
        ).pack(side='left')

        self._status_label = ctk.CTkLabel(
            header, text='●  Stopped',
            font=ctk.CTkFont(family='Segoe UI', size=13),
            text_color=self.RED
        )
        self._status_label.pack(side='right')

        # Separator
        ctk.CTkFrame(self.app, fg_color=self.BORDER, height=1).pack(fill='x', padx=28, pady=(14, 0))

        # ─── Engine Toggle ───────────────────────────────
        self._toggle_btn = ctk.CTkButton(
            self.app,
            text='▶   START JARVIS',
            font=ctk.CTkFont(family='Segoe UI', size=15, weight='bold'),
            fg_color=self.ACCENT,
            text_color=self.BG,
            hover_color=self.ACCENT_DARK,
            corner_radius=12,
            height=52,
            command=self._toggle_engine
        )
        self._toggle_btn.pack(fill='x', padx=28, pady=(18, 0))

        # ─── Personalization Section ─────────────────────
        ctk.CTkFrame(self.app, fg_color=self.BORDER, height=1).pack(fill='x', padx=28, pady=(20, 0))

        ctk.CTkLabel(
            self.app, text='PERSONALIZATION',
            font=ctk.CTkFont(family='Consolas', size=11, weight='bold'),
            text_color=self.DIM
        ).pack(anchor='w', padx=32, pady=(14, 0))

        card = ctk.CTkFrame(self.app, fg_color=self.CARD, corner_radius=12)
        card.pack(fill='x', padx=28, pady=(8, 0))

        # Name
        ctk.CTkLabel(card, text='Your Name', font=ctk.CTkFont(size=12), text_color=self.DIM).pack(anchor='w', padx=16, pady=(14, 0))
        self._name_entry = ctk.CTkEntry(
            card, placeholder_text='e.g. Alfie',
            font=ctk.CTkFont(size=14),
            fg_color=self.INPUT, text_color=self.TEXT,
            border_color=self.BORDER, corner_radius=8, height=38
        )
        self._name_entry.pack(fill='x', padx=16, pady=(4, 0))

        # Wake Words
        ctk.CTkLabel(card, text='Wake / Trigger Words  (comma separated)', font=ctk.CTkFont(size=12), text_color=self.DIM).pack(anchor='w', padx=16, pady=(12, 0))
        self._wake_entry = ctk.CTkEntry(
            card, placeholder_text='jarvis, hey jarvis, ok jarvis',
            font=ctk.CTkFont(size=14),
            fg_color=self.INPUT, text_color=self.TEXT,
            border_color=self.BORDER, corner_radius=8, height=38
        )
        self._wake_entry.pack(fill='x', padx=16, pady=(4, 0))

        # Vision Keywords
        ctk.CTkLabel(card, text='Extra Vision Keywords  (comma separated)', font=ctk.CTkFont(size=12), text_color=self.DIM).pack(anchor='w', padx=16, pady=(12, 0))
        self._vision_entry = ctk.CTkEntry(
            card, placeholder_text='diagram, flowchart, architecture',
            font=ctk.CTkFont(size=14),
            fg_color=self.INPUT, text_color=self.TEXT,
            border_color=self.BORDER, corner_radius=8, height=38
        )
        self._vision_entry.pack(fill='x', padx=16, pady=(4, 0))

        # Save Button
        self._save_btn = ctk.CTkButton(
            card,
            text='💾   SAVE SETTINGS',
            font=ctk.CTkFont(family='Segoe UI', size=13, weight='bold'),
            fg_color=self.INPUT,
            text_color=self.ACCENT,
            hover_color=self.BORDER,
            corner_radius=8,
            height=40,
            command=self._save_settings
        )
        self._save_btn.pack(fill='x', padx=16, pady=(14, 16))

        # ─── Monitored Paths Section ─────────────────────
        ctk.CTkFrame(self.app, fg_color=self.BORDER, height=1).pack(fill='x', padx=28, pady=(16, 0))

        ctk.CTkLabel(
            self.app, text='MONITORED PATHS',
            font=ctk.CTkFont(family='Consolas', size=11, weight='bold'),
            text_color=self.DIM
        ).pack(anchor='w', padx=32, pady=(14, 0))

        path_card = ctk.CTkFrame(self.app, fg_color=self.CARD, corner_radius=12)
        path_card.pack(fill='both', expand=True, padx=28, pady=(8, 0))

        # Path list using a CTkTextbox for scrollability
        self._path_textbox = ctk.CTkTextbox(
            path_card,
            font=ctk.CTkFont(family='Consolas', size=12),
            fg_color=self.INPUT,
            text_color=self.TEXT,
            corner_radius=8,
            height=90,
            state='disabled'
        )
        self._path_textbox.pack(fill='both', expand=True, padx=12, pady=(12, 6))

        # Action buttons row
        btn_row = ctk.CTkFrame(path_card, fg_color='transparent')
        btn_row.pack(fill='x', padx=12, pady=(0, 12))

        ctk.CTkButton(
            btn_row, text='📁  Add Folder', width=130,
            font=ctk.CTkFont(size=12),
            fg_color=self.INPUT, text_color=self.ACCENT,
            hover_color=self.BORDER, corner_radius=8, height=32,
            command=self._add_folder
        ).pack(side='left', padx=(0, 6))

        ctk.CTkButton(
            btn_row, text='📄  Add File', width=120,
            font=ctk.CTkFont(size=12),
            fg_color=self.INPUT, text_color=self.ACCENT,
            hover_color=self.BORDER, corner_radius=8, height=32,
            command=self._add_file
        ).pack(side='left', padx=(0, 6))

        ctk.CTkButton(
            btn_row, text='✕  Remove Last', width=130,
            font=ctk.CTkFont(size=12),
            fg_color=self.INPUT, text_color=self.RED,
            hover_color=self.BORDER, corner_radius=8, height=32,
            command=self._remove_last_path
        ).pack(side='right')

        # ─── Footer ──────────────────────────────────────
        ctk.CTkLabel(
            self.app,
            text='100 % Offline  •  Zero Cloud  •  RAM Only',
            font=ctk.CTkFont(family='Consolas', size=10),
            text_color='#3A3A4A'
        ).pack(pady=(10, 10))

    # ══════════════════════════════════════════════════════════════
    #  SETTINGS I/O
    # ══════════════════════════════════════════════════════════════

    def _load_fields(self):
        s = self._settings
        self._name_entry.insert(0, s.get('user_name', ''))
        self._wake_entry.insert(0, ', '.join(s.get('wake_words', [])))
        self._vision_entry.insert(0, ', '.join(s.get('vision_keywords', [])))
        self._refresh_path_list()

    def _refresh_path_list(self):
        paths = self._settings.get('custom_paths', [])
        self._path_textbox.configure(state='normal')
        self._path_textbox.delete('1.0', 'end')
        for p in paths:
            self._path_textbox.insert('end', p + '\n')
        self._path_textbox.configure(state='disabled')

    def _save_settings(self):
        name = self._name_entry.get().strip()
        wake_raw = self._wake_entry.get().strip()
        vision_raw = self._vision_entry.get().strip()

        wake_words = [w.strip().lower() for w in wake_raw.split(',') if w.strip()]
        vision_kw  = [w.strip().lower() for w in vision_raw.split(',') if w.strip()]

        # Auto-add name as wake word
        if name and name.lower() not in wake_words:
            wake_words.append(name.lower())

        self._settings['user_name'] = name
        self._settings['wake_words'] = wake_words
        self._settings['vision_keywords'] = vision_kw
        settings_manager.save_settings(self._settings)

        # Flash confirmation
        self._save_btn.configure(text='✓  Saved!', text_color=self.ACCENT)
        self.app.after(1500, lambda: self._save_btn.configure(text='💾   SAVE SETTINGS', text_color=self.ACCENT))

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
                self._refresh_path_list()

    def _add_file(self):
        path = filedialog.askopenfilename(title='Select a file for JARVIS to monitor')
        if path:
            paths = self._settings.get('custom_paths', [])
            if path not in paths:
                paths.append(path)
                self._settings['custom_paths'] = paths
                settings_manager.save_settings(self._settings)
                self._refresh_path_list()

    def _remove_last_path(self):
        paths = self._settings.get('custom_paths', [])
        if paths:
            paths.pop()
            self._settings['custom_paths'] = paths
            settings_manager.save_settings(self._settings)
            self._refresh_path_list()

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
            hover_color='#CC5555'
        )
        self._status_label.configure(text='●  Running', text_color=self.ACCENT)

        # Create a SEPARATE hidden Tk root for ghost overlays
        # This prevents the dashboard from being affected
        def _create_ghost_root():
            self._ghost_root = tk.Toplevel(self.app)
            self._ghost_root.withdraw()

        self.app.after(0, _create_ghost_root)

        self._engine_thread = threading.Thread(
            target=self._engine_worker,
            daemon=True
        )
        self._engine_thread.start()

    def _stop_engine(self):
        self._stop_event.set()
        self._engine_running = False

        self._toggle_btn.configure(
            text='▶   START JARVIS',
            fg_color=self.ACCENT,
            text_color=self.BG,
            hover_color=self.ACCENT_DARK
        )
        self._status_label.configure(text='●  Stopped', text_color=self.RED)

        # Destroy ghost root
        if self._ghost_root:
            try:
                self._ghost_root.destroy()
            except Exception:
                pass
            self._ghost_root = None
            self._overlay = None

    def _engine_worker(self):
        """Runs the JARVIS live engine in a background thread."""
        try:
            from context_engine import get_suggestion, prewarm_ollama
            from audio_listener import AudioListener
            from screen_reader import ScreenReader

            prewarm_ollama()

            # Wait for ghost_root to be created
            import time
            for _ in range(50):
                if self._ghost_root:
                    break
                time.sleep(0.1)

            # Create overlay on the hidden ghost root (in main thread)
            overlay_ready = threading.Event()

            def _create_overlay():
                try:
                    from ghost_overlay import GhostOverlay
                    self._overlay = GhostOverlay(self._ghost_root)
                except Exception as e:
                    print(f'⚠️  Overlay creation failed: {e}')
                overlay_ready.set()

            self.app.after(0, _create_overlay)
            overlay_ready.wait(timeout=5)

            screen = ScreenReader()
            try:
                if self._overlay:
                    hwnd = self._overlay.get_hwnd()
                    screen.set_overlay_hwnd(hwnd)
            except Exception:
                pass

            # Setup hotkey
            try:
                import keyboard
                def on_hotkey():
                    try:
                        screen_b64 = screen.get_latest()
                        if screen_b64 and self._overlay:
                            suggestion = get_suggestion(
                                "Analyze this screen carefully. Identify bugs, errors, or improvements. Give specific actionable feedback.",
                                screen_b64, force_vision=True
                            )
                            if suggestion and suggestion != 'SILENT':
                                self._overlay.show_popup(suggestion, "hotkey screen scan")
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
            print('🧠 JARVIS engine stopped from GUI')

        except Exception as e:
            print(f'⚠️  Engine error: {e}')
            self.app.after(0, self._stop_engine)

    # ══════════════════════════════════════════════════════════════
    #  APP LIFECYCLE
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
    """Entry point for the dashboard."""
    app = JarvisDashboard()
    app.run()


if __name__ == '__main__':
    launch()
