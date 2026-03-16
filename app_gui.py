# JARVIS Dashboard — Dark-themed GUI for managing the AI assistant.
# PRIVACY: Uses settings_manager.py for the ONLY disk writes (settings.json).
import tkinter as tk
from tkinter import filedialog
import threading
import sys
import os

import settings_manager


class JarvisDashboard:
    """Main application window for JARVIS control and personalization."""

    # ── Color Palette ─────────────────────────────────────────────
    BG          = '#0A0F1A'
    BG_CARD     = '#0D1117'
    BG_INPUT    = '#161B22'
    BORDER      = '#1C2128'
    ACCENT      = '#4DFFB4'
    ACCENT_DIM  = '#1F6648'
    TEXT        = '#E6EDF3'
    TEXT_DIM    = '#7D8590'
    RED         = '#FF6B6B'
    ORANGE      = '#FFB347'
    FONT_FAMILY = 'Segoe UI'

    def __init__(self):
        self.root = tk.Tk()
        self.root.title('JARVIS — Control Panel')
        self.root.configure(bg=self.BG)
        self.root.resizable(False, False)

        # Center the window on screen
        win_w, win_h = 520, 680
        sx = (self.root.winfo_screenwidth() - win_w) // 2
        sy = (self.root.winfo_screenheight() - win_h) // 2
        self.root.geometry(f'{win_w}x{win_h}+{sx}+{sy}')

        # State
        self._engine_running = False
        self._engine_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._settings = settings_manager.load_settings()

        self._build_ui()
        self._load_fields_from_settings()

    # ── UI Construction ───────────────────────────────────────────

    def _build_ui(self):
        # ─ Header ─────────────────────────────────────────
        header = tk.Frame(self.root, bg=self.BG, height=70)
        header.pack(fill='x', padx=24, pady=(18, 0))
        header.pack_propagate(False)

        tk.Label(
            header, text='⚡  JARVIS',
            font=(self.FONT_FAMILY, 22, 'bold'),
            fg=self.ACCENT, bg=self.BG, anchor='w'
        ).pack(side='left')

        self._status_dot = tk.Label(
            header, text='●  Stopped',
            font=(self.FONT_FAMILY, 11),
            fg=self.RED, bg=self.BG, anchor='e'
        )
        self._status_dot.pack(side='right')

        # Separator
        tk.Frame(self.root, bg=self.BORDER, height=1).pack(fill='x', padx=24, pady=(10, 0))

        # ─ Start / Stop Button ────────────────────────────
        btn_frame = tk.Frame(self.root, bg=self.BG)
        btn_frame.pack(fill='x', padx=24, pady=(18, 0))

        self._toggle_btn = tk.Button(
            btn_frame,
            text='▶   START JARVIS',
            font=(self.FONT_FAMILY, 13, 'bold'),
            fg=self.BG,
            bg=self.ACCENT,
            activebackground=self.ACCENT_DIM,
            activeforeground=self.TEXT,
            relief='flat',
            cursor='hand2',
            padx=20, pady=10,
            command=self._toggle_engine
        )
        self._toggle_btn.pack(fill='x', ipady=4)

        # ─ Personalization Card ───────────────────────────
        tk.Frame(self.root, bg=self.BORDER, height=1).pack(fill='x', padx=24, pady=(18, 0))

        card_label = tk.Label(
            self.root, text='PERSONALIZATION',
            font=('Consolas', 9, 'bold'),
            fg=self.TEXT_DIM, bg=self.BG, anchor='w'
        )
        card_label.pack(fill='x', padx=28, pady=(14, 0))

        card = tk.Frame(self.root, bg=self.BG_CARD, padx=16, pady=14)
        card.pack(fill='x', padx=24, pady=(6, 0))

        # Name
        tk.Label(card, text='Your Name', font=(self.FONT_FAMILY, 10), fg=self.TEXT_DIM, bg=self.BG_CARD, anchor='w').pack(fill='x')
        self._name_var = tk.StringVar()
        name_entry = tk.Entry(
            card, textvariable=self._name_var,
            font=(self.FONT_FAMILY, 12), bg=self.BG_INPUT, fg=self.TEXT,
            insertbackground=self.ACCENT, relief='flat', bd=6
        )
        name_entry.pack(fill='x', ipady=4, pady=(2, 10))

        # Wake Words
        tk.Label(card, text='Wake / Trigger Words  (comma separated)', font=(self.FONT_FAMILY, 10), fg=self.TEXT_DIM, bg=self.BG_CARD, anchor='w').pack(fill='x')
        self._wake_var = tk.StringVar()
        wake_entry = tk.Entry(
            card, textvariable=self._wake_var,
            font=(self.FONT_FAMILY, 12), bg=self.BG_INPUT, fg=self.TEXT,
            insertbackground=self.ACCENT, relief='flat', bd=6
        )
        wake_entry.pack(fill='x', ipady=4, pady=(2, 10))

        # Extra Vision Keywords
        tk.Label(card, text='Extra Vision Keywords  (comma separated)', font=(self.FONT_FAMILY, 10), fg=self.TEXT_DIM, bg=self.BG_CARD, anchor='w').pack(fill='x')
        self._vision_var = tk.StringVar()
        vision_entry = tk.Entry(
            card, textvariable=self._vision_var,
            font=(self.FONT_FAMILY, 12), bg=self.BG_INPUT, fg=self.TEXT,
            insertbackground=self.ACCENT, relief='flat', bd=6
        )
        vision_entry.pack(fill='x', ipady=4, pady=(2, 4))

        # ─ Save Button ────────────────────────────────────
        save_btn = tk.Button(
            card, text='💾  SAVE SETTINGS',
            font=(self.FONT_FAMILY, 10, 'bold'),
            fg=self.ACCENT, bg=self.BG_INPUT,
            activebackground=self.BORDER,
            activeforeground=self.TEXT,
            relief='flat', cursor='hand2',
            padx=12, pady=6,
            command=self._save_settings
        )
        save_btn.pack(fill='x', ipady=2, pady=(8, 0))

        # ─ Monitored Paths Card ──────────────────────────
        tk.Frame(self.root, bg=self.BORDER, height=1).pack(fill='x', padx=24, pady=(18, 0))

        path_label = tk.Label(
            self.root, text='MONITORED PATHS',
            font=('Consolas', 9, 'bold'),
            fg=self.TEXT_DIM, bg=self.BG, anchor='w'
        )
        path_label.pack(fill='x', padx=28, pady=(14, 0))

        path_card = tk.Frame(self.root, bg=self.BG_CARD, padx=16, pady=10)
        path_card.pack(fill='both', expand=True, padx=24, pady=(6, 0))

        # Path list (scrollable)
        self._path_listbox = tk.Listbox(
            path_card,
            font=('Consolas', 10),
            bg=self.BG_INPUT, fg=self.TEXT,
            selectbackground=self.ACCENT_DIM,
            selectforeground=self.TEXT,
            relief='flat', bd=4,
            height=5
        )
        self._path_listbox.pack(fill='both', expand=True, pady=(0, 6))

        path_btn_row = tk.Frame(path_card, bg=self.BG_CARD)
        path_btn_row.pack(fill='x')

        add_folder_btn = tk.Button(
            path_btn_row, text='📁  Add Folder',
            font=(self.FONT_FAMILY, 9), fg=self.ACCENT, bg=self.BG_INPUT,
            activebackground=self.BORDER, relief='flat', cursor='hand2',
            padx=8, pady=4,
            command=self._add_folder
        )
        add_folder_btn.pack(side='left', padx=(0, 4))

        add_file_btn = tk.Button(
            path_btn_row, text='📄  Add File',
            font=(self.FONT_FAMILY, 9), fg=self.ACCENT, bg=self.BG_INPUT,
            activebackground=self.BORDER, relief='flat', cursor='hand2',
            padx=8, pady=4,
            command=self._add_file
        )
        add_file_btn.pack(side='left', padx=(0, 4))

        remove_btn = tk.Button(
            path_btn_row, text='✕  Remove',
            font=(self.FONT_FAMILY, 9), fg=self.RED, bg=self.BG_INPUT,
            activebackground=self.BORDER, relief='flat', cursor='hand2',
            padx=8, pady=4,
            command=self._remove_path
        )
        remove_btn.pack(side='right')

        # ─ Footer ────────────────────────────────────────
        footer = tk.Frame(self.root, bg=self.BG, height=36)
        footer.pack(fill='x', padx=24, pady=(8, 10))
        tk.Label(
            footer, text='100 % Offline  •  Zero Cloud  •  RAM Only',
            font=('Consolas', 8), fg=self.TEXT_DIM, bg=self.BG
        ).pack(side='left')

    # ── Field loading / saving ────────────────────────────────────

    def _load_fields_from_settings(self):
        s = self._settings
        self._name_var.set(s.get('user_name', ''))
        self._wake_var.set(', '.join(s.get('wake_words', [])))
        self._vision_var.set(', '.join(s.get('vision_keywords', [])))

        self._path_listbox.delete(0, 'end')
        for p in s.get('custom_paths', []):
            self._path_listbox.insert('end', p)

    def _save_settings(self):
        name = self._name_var.get().strip()
        wake_raw = self._wake_var.get().strip()
        vision_raw = self._vision_var.get().strip()

        wake_words = [w.strip().lower() for w in wake_raw.split(',') if w.strip()]
        vision_kw  = [w.strip().lower() for w in vision_raw.split(',') if w.strip()]

        # Auto-add user name as a wake word if provided
        if name and name.lower() not in wake_words:
            wake_words.append(name.lower())

        paths = list(self._path_listbox.get(0, 'end'))

        self._settings = {
            'user_name': name,
            'wake_words': wake_words,
            'vision_keywords': vision_kw,
            'custom_paths': paths,
        }
        settings_manager.save_settings(self._settings)

        # Flash save confirmation
        self._flash_status('✓  Settings saved', self.ACCENT)

    # ── Path management ───────────────────────────────────────────

    def _add_folder(self):
        path = filedialog.askdirectory(title='Select a folder for JARVIS to monitor')
        if path:
            self._path_listbox.insert('end', path)
            self._auto_save_paths()

    def _add_file(self):
        path = filedialog.askopenfilename(title='Select a file for JARVIS to monitor')
        if path:
            self._path_listbox.insert('end', path)
            self._auto_save_paths()

    def _remove_path(self):
        sel = self._path_listbox.curselection()
        if sel:
            self._path_listbox.delete(sel[0])
            self._auto_save_paths()

    def _auto_save_paths(self):
        paths = list(self._path_listbox.get(0, 'end'))
        self._settings['custom_paths'] = paths
        settings_manager.save_settings(self._settings)

    # ── Engine control ────────────────────────────────────────────

    def _toggle_engine(self):
        if self._engine_running:
            self._stop_engine()
        else:
            self._start_engine()

    def _start_engine(self):
        self._stop_event.clear()
        self._engine_running = True

        self._toggle_btn.config(
            text='■   STOP JARVIS',
            bg=self.RED,
            fg=self.TEXT
        )
        self._status_dot.config(text='●  Running', fg=self.ACCENT)

        self._engine_thread = threading.Thread(
            target=self._engine_worker,
            daemon=True
        )
        self._engine_thread.start()

    def _stop_engine(self):
        self._stop_event.set()
        self._engine_running = False
        self._toggle_btn.config(
            text='▶   START JARVIS',
            bg=self.ACCENT,
            fg=self.BG
        )
        self._status_dot.config(text='●  Stopped', fg=self.RED)

    def _engine_worker(self):
        """Runs the JARVIS live engine in a background thread."""
        try:
            from context_engine import get_suggestion, prewarm_ollama
            from audio_listener import AudioListener
            from screen_reader import ScreenReader
            from ghost_overlay import GhostOverlay

            prewarm_ollama()

            # Build overlay in main thread
            overlay_ref = [None]
            ready_event = threading.Event()

            def create_overlay():
                overlay_ref[0] = GhostOverlay(self.root)
                ready_event.set()

            self.root.after(0, create_overlay)
            ready_event.wait(timeout=5)
            overlay = overlay_ref[0]

            screen = ScreenReader()
            try:
                if overlay:
                    hwnd = overlay.get_hwnd()
                    screen.set_overlay_hwnd(hwnd)
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
                        if suggestion != 'SILENT' and overlay:
                            print(f'⚡ Suggestion: {suggestion}')
                            overlay.show_popup(suggestion, audio_text)
                        else:
                            print('   (SILENT)')
                except Exception:
                    continue

            audio.stop()
            screen.stop()
            print('🧠 JARVIS engine stopped from GUI')

        except Exception as e:
            print(f'⚠️  Engine error: {e}')
            self.root.after(0, self._stop_engine)

    # ── Helpers ───────────────────────────────────────────────────

    def _flash_status(self, msg: str, color: str):
        original_text = self._status_dot.cget('text')
        original_fg = self._status_dot.cget('fg')
        self._status_dot.config(text=msg, fg=color)
        self.root.after(2000, lambda: self._status_dot.config(text=original_text, fg=original_fg))

    def run(self):
        self.root.protocol('WM_DELETE_WINDOW', self._on_close)
        self.root.mainloop()

    def _on_close(self):
        if self._engine_running:
            self._stop_engine()
        self.root.destroy()
        sys.exit(0)


def launch():
    """Entry point for the dashboard."""
    app = JarvisDashboard()
    app.run()


if __name__ == '__main__':
    launch()
