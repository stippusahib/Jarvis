# JARVIS Dashboard — Premium dark-themed GUI using CustomTkinter.
# PRIVACY: Uses settings_manager.py for the ONLY disk writes (settings.json).
import os
os.environ.setdefault('FOR_DISABLE_CONSOLE_CTRL_HANDLER', '1')

import customtkinter as ctk
from tkinter import filedialog
import tkinter as tk
import threading
import sys
import pathlib

import settings_manager

try:
    import keyboard
    HAS_KEYBOARD = True
except Exception:
    HAS_KEYBOARD = False

# ── DPI is set in main.py before any tkinter import ──────────

from context_engine import get_suggestion, get_command_response, prewarm_ollama
from audio_listener import AudioListener
from screen_reader import ScreenReader
from voice_engine import VoiceEngine
from command_parser import parse as parse_command, get_human_description
from os_controller import OSController
from permission_manager import PermissionManager, log_action
from ghost_overlay import GhostOverlay

# Theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# Icon path
ICON_PATH = pathlib.Path(__file__).parent / "jarvis_icon.png"


class JarvisDashboard:
    """Premium control panel for JARVIS."""

    # ── Palette ───────────────────────────────────────────────────
    # Zinc + Emerald palette — no AI purple, no pure black
    BG_DEEP     = '#09090B'   # zinc-950
    BG          = '#18181B'   # zinc-900
    CARD        = '#27272A'   # zinc-800
    INPUT       = '#3F3F46'   # zinc-700
    BORDER      = '#3F3F46'   # zinc-700
    ACCENT      = '#10B981'   # emerald-500
    ACCENT_DARK = '#059669'   # emerald-600
    ACCENT_GLOW = '#34D399'   # emerald-400
    TEXT        = '#FAFAFA'   # zinc-50
    TEXT_SEC    = '#A1A1AA'   # zinc-400
    DIM         = '#71717A'   # zinc-500
    RED         = '#EF4444'
    RED_DARK    = '#DC2626'
    ORANGE      = '#F59E0B'
    GREEN_SOFT  = '#22C55E'

    def __init__(self):
        self.app = ctk.CTk()
        self.app.title('JARVIS')
        self.app.configure(fg_color=self.BG_DEEP)
        self.app.resizable(False, False)

        # Window icon — use .ico for Windows taskbar
        ICO_PATH = pathlib.Path(__file__).parent / "jarvis_icon.ico"
        try:
            if ICO_PATH.exists():
                self.app.iconbitmap(str(ICO_PATH))
                # Also set the AppUserModelID so Windows groups the taskbar icon
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('jarvis.secondbrain.app')  # type: ignore
        except Exception:
            pass
        try:
            if ICON_PATH.exists():
                icon_img = tk.PhotoImage(file=str(ICON_PATH))
                self.app.iconphoto(True, icon_img)
                self._icon_ref = icon_img
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
        self._tray = None

        # System tray icon
        try:
            from tray import create_tray_icon
            self._tray = create_tray_icon(lambda: self.app.after(0, self._on_close))
        except Exception:
            pass

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
            top, text='  JARVIS',
            font=ctk.CTkFont(family='Cascadia Code', size=18, weight='bold'),
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
            text='Ctrl+Shift+J  ·  Mic  ·  Vision',
            font=ctk.CTkFont(family='Cascadia Code', size=10),
            text_color=self.DIM
        )
        self._engine_info.pack(side='left')

        self._listening_indicator = ctk.CTkLabel(
            info_row,
            text='LISTENING',
            font=ctk.CTkFont(family='Cascadia Code', size=11, weight='bold'),
            text_color=self.ACCENT
        )

        # ─── Device Card ─────────────────────────────────
        device_card = ctk.CTkFrame(scroll, fg_color=self.CARD, corner_radius=14)
        device_card.pack(fill='x', padx=20, pady=(12, 0))

        device_inner = ctk.CTkFrame(device_card, fg_color='transparent')
        device_inner.pack(fill='x', padx=20, pady=18)

        device_header = ctk.CTkFrame(device_inner, fg_color='transparent')
        device_header.pack(fill='x')

        ctk.CTkLabel(
            device_header, text='DEVICE',
            font=ctk.CTkFont(family='Consolas', size=10, weight='bold'),
            text_color=self.DIM
        ).pack(side='left')

        # Model Info button (top-right)
        self._info_btn = ctk.CTkButton(
            device_header, text='Models', width=80,
            font=ctk.CTkFont(size=11),
            fg_color='transparent', text_color=self.ACCENT,
            hover_color=self.BORDER, corner_radius=6, height=26,
            command=self._show_model_info
        )
        self._info_btn.pack(side='right')

        # Device summary (populated after analysis)
        self._device_summary = ctk.CTkLabel(
            device_inner, text='No profile — click Analyse to optimize',
            font=ctk.CTkFont(family='Consolas', size=10),
            text_color=self.DIM, anchor='w'
        )
        self._device_summary.pack(fill='x', pady=(8, 0))

        # Analyse button
        self._analyse_btn = ctk.CTkButton(
            device_inner,
            text='ANALYSE DEVICE',
            font=ctk.CTkFont(size=13, weight='bold'),
            fg_color=self.INPUT, text_color=self.ACCENT,
            hover_color=self.BORDER, corner_radius=8, height=40,
            command=self._analyse_device
        )
        self._analyse_btn.pack(fill='x', pady=(10, 0))

        # Load existing profile if available
        self._refresh_device_summary()

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
            text='SAVE',
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
            btn_row, text='+ Folder', width=100,
            font=ctk.CTkFont(size=11),
            fg_color=self.INPUT, text_color=self.ACCENT,
            hover_color=self.BORDER, corner_radius=8, height=32,
            command=self._add_folder
        ).pack(side='left', padx=(0, 6))

        ctk.CTkButton(
            btn_row, text='+ File', width=90,
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

        # ─── OS Control Card ─────────────────────────────
        os_card = ctk.CTkFrame(scroll, fg_color=self.CARD, corner_radius=14)
        os_card.pack(fill='x', padx=20, pady=(12, 0))

        os_inner = ctk.CTkFrame(os_card, fg_color='transparent')
        os_inner.pack(fill='x', padx=20, pady=18)

        ctk.CTkLabel(
            os_inner, text='OS CONTROL',
            font=ctk.CTkFont(family='Consolas', size=10, weight='bold'),
            text_color=self.DIM
        ).pack(anchor='w')

        ctk.CTkLabel(
            os_inner, text='Enable voice commands to control your laptop',
            font=ctk.CTkFont(size=10), text_color=self.DIM
        ).pack(anchor='w', pady=(2, 8))

        # Toggle switches
        self._os_app_var = ctk.BooleanVar(value=self._settings.get('os_control_enabled', True))
        self._os_file_var = ctk.BooleanVar(value=self._settings.get('file_control_enabled', True))
        self._os_system_var = ctk.BooleanVar(value=self._settings.get('system_control_enabled', True))
        self._os_auto_var = ctk.BooleanVar(value=self._settings.get('auto_execute_safe', True))

        def _toggle_row(parent, text, var, desc=''):
            row = ctk.CTkFrame(parent, fg_color='transparent')
            row.pack(fill='x', pady=3)
            ctk.CTkLabel(
                row, text=text,
                font=ctk.CTkFont(size=12, weight='bold'),
                text_color=self.TEXT_SEC
            ).pack(side='left')
            sw = ctk.CTkSwitch(
                row, text='', variable=var,
                width=42, height=22,
                fg_color=self.BORDER,
                progress_color=self.ACCENT,
                command=self._save_os_settings
            )
            sw.pack(side='right')
            if desc:
                ctk.CTkLabel(
                    parent, text=desc,
                    font=ctk.CTkFont(size=9), text_color=self.DIM
                ).pack(anchor='w', pady=(0, 2))

        _toggle_row(os_inner, 'App Control', self._os_app_var, 'Open, close, switch apps by voice')
        _toggle_row(os_inner, 'File Control', self._os_file_var, 'Create, delete, move, search files')
        _toggle_row(os_inner, 'System Control', self._os_system_var, 'Volume, brightness, WiFi, power')
        _toggle_row(os_inner, 'Auto-Execute Safe', self._os_auto_var, 'Skip confirmation for safe commands')

        # ─── Voice Card ──────────────────────────────────
        voice_card = ctk.CTkFrame(scroll, fg_color=self.CARD, corner_radius=14)
        voice_card.pack(fill='x', padx=20, pady=(12, 0))

        voice_inner = ctk.CTkFrame(voice_card, fg_color='transparent')
        voice_inner.pack(fill='x', padx=20, pady=18)

        ctk.CTkLabel(
            voice_inner, text='VOICE',
            font=ctk.CTkFont(family='Consolas', size=10, weight='bold'),
            text_color=self.DIM
        ).pack(anchor='w')

        ctk.CTkLabel(
            voice_inner, text='JARVIS speaks responses aloud',
            font=ctk.CTkFont(size=10), text_color=self.DIM
        ).pack(anchor='w', pady=(2, 8))

        # Voice enable
        self._voice_enabled_var = ctk.BooleanVar(value=self._settings.get('voice_enabled', True))
        voice_en_row = ctk.CTkFrame(voice_inner, fg_color='transparent')
        voice_en_row.pack(fill='x', pady=3)
        ctk.CTkLabel(
            voice_en_row, text='Voice Enabled',
            font=ctk.CTkFont(size=12, weight='bold'),
            text_color=self.TEXT_SEC
        ).pack(side='left')
        ctk.CTkSwitch(
            voice_en_row, text='', variable=self._voice_enabled_var,
            width=42, height=22,
            fg_color=self.BORDER,
            progress_color=self.ACCENT,
            command=self._save_voice_settings
        ).pack(side='right')

        # Speed slider
        ctk.CTkLabel(
            voice_inner, text='Speech Speed',
            font=ctk.CTkFont(size=11, weight='bold'), text_color=self.TEXT_SEC
        ).pack(anchor='w', pady=(10, 0))

        speed_row = ctk.CTkFrame(voice_inner, fg_color='transparent')
        speed_row.pack(fill='x', pady=(4, 0))

        self._speed_label = ctk.CTkLabel(
            speed_row, text=f"{self._settings.get('voice_speed', 175)} wpm",
            font=ctk.CTkFont(family='Consolas', size=10), text_color=self.DIM,
            width=60
        )
        self._speed_label.pack(side='right')

        self._speed_slider = ctk.CTkSlider(
            speed_row, from_=100, to=300,
            number_of_steps=20,
            fg_color=self.INPUT,
            progress_color=self.ACCENT,
            button_color=self.ACCENT_GLOW,
            button_hover_color=self.ACCENT,
            command=self._on_speed_change
        )
        self._speed_slider.set(self._settings.get('voice_speed', 175))
        self._speed_slider.pack(side='left', fill='x', expand=True, padx=(0, 8))

        # Test and Stop Voice buttons
        voice_btn_row = ctk.CTkFrame(voice_inner, fg_color='transparent')
        voice_btn_row.pack(fill='x', pady=(12, 0))

        ctk.CTkButton(
            voice_btn_row,
            text='Test Voice',
            font=ctk.CTkFont(size=11),
            fg_color=self.INPUT, text_color=self.ACCENT,
            hover_color=self.BORDER, corner_radius=8, height=32,
            command=self._test_voice
        ).pack(side='left', fill='x', expand=True, padx=(0, 4))

        ctk.CTkButton(
            voice_btn_row,
            text='Stop Voice',
            font=ctk.CTkFont(size=11),
            fg_color=self.INPUT, text_color=self.RED,
            hover_color=self.BORDER, corner_radius=8, height=32,
            command=self._stop_voice
        ).pack(side='right', fill='x', expand=True, padx=(4, 0))

        # ─── Footer ──────────────────────────────────────
        footer = ctk.CTkFrame(scroll, fg_color='transparent')
        footer.pack(fill='x', padx=20, pady=(16, 16))

        ctk.CTkLabel(
            footer,
            text='Voice Controlled  •  Full OS Access  •  Offline  •  Private',
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
        self._save_btn.configure(text='SAVED', fg_color=self.ACCENT_DARK, text_color=self.ACCENT_GLOW)
        self.app.after(1500, lambda: self._save_btn.configure(
            text='SAVE', fg_color=self.INPUT, text_color=self.ACCENT
        ))

    def _save_os_settings(self):
        """Save OS control toggles to settings."""
        self._settings['os_control_enabled'] = self._os_app_var.get()
        self._settings['file_control_enabled'] = self._os_file_var.get()
        self._settings['system_control_enabled'] = self._os_system_var.get()
        self._settings['auto_execute_safe'] = self._os_auto_var.get()
        settings_manager.save_settings(self._settings)

    def _save_voice_settings(self):
        """Save voice settings."""
        self._settings['voice_enabled'] = self._voice_enabled_var.get()
        settings_manager.save_settings(self._settings)

    def _on_speed_change(self, value):
        """Speed slider callback."""
        speed = int(value)
        self._speed_label.configure(text=f'{speed} wpm')
        self._settings['voice_speed'] = speed
        settings_manager.save_settings(self._settings)

    def _test_voice(self):
        """Test TTS in a background thread."""
        def _do_test():
            try:
                from voice_engine import VoiceEngine
                test_ve = VoiceEngine()
                test_ve._speed = self._settings.get('voice_speed', 175)
                test_ve._volume = self._settings.get('voice_volume', 0.9)
                test_ve.start()
                import time
                time.sleep(0.5)
                test_ve.speak_and_wait('JARVIS online. All systems operational, sir.', timeout=8)
                test_ve.stop()
            except Exception as e:
                print(f'⚠️  Voice test failed: {e}')
        threading.Thread(target=_do_test, daemon=True).start()

    # ══════════════════════════════════════════════════════════════
    #  DEVICE ANALYSIS
    # ══════════════════════════════════════════════════════════════

    def _analyse_device(self):
        """Run device analysis in a background thread with cancel support."""
        if hasattr(self, '_analyse_cancel') and self._analyse_cancel:
            # Cancel was pressed
            self._analyse_cancel.set()
            self._analyse_cancel = None  # Reset state so we can analyse again
            self._analyse_btn.configure(
                text='ANALYSE DEVICE', state='normal',
                fg_color=self.INPUT, text_color=self.ACCENT
            )
            self._device_summary.configure(text='Cancelled', text_color=self.DIM)
            return

        self._analyse_cancel = threading.Event()
        self._analyse_btn.configure(
            text='✕  CANCEL', state='normal',
            fg_color=self.RED, text_color=self.TEXT,
            hover_color=self.RED_DARK
        )
        self._device_summary.configure(text='Starting analysis...')

        def _progress(msg):
            self.app.after(0, lambda: self._device_summary.configure(text=msg))

        def _run():
            try:
                import device_analyzer
                profile = device_analyzer.analyse(
                    progress_callback=_progress,
                    cancel_event=self._analyse_cancel
                )
                if profile is None:
                    return  # Cancelled silently
                self.app.after(0, lambda: self._on_analysis_done(profile))
            except Exception as e:
                error_msg = str(e)
                self.app.after(0, lambda msg=error_msg: self._on_analysis_done(None, msg))

        threading.Thread(target=_run, daemon=True).start()

    def _on_analysis_done(self, profile, error=None):
        """Called when analysis completes — update UI."""
        self._analyse_cancel = None
        self._analyse_btn.configure(
            text='🔍  ANALYSE DEVICE', state='normal',
            fg_color=self.INPUT, text_color=self.ACCENT,
            hover_color=self.BORDER
        )
        if error:
            self._device_summary.configure(text=f'⚠️  Error: {error}', text_color=self.RED)
            return

        self._refresh_device_summary()

        # Flash success
        self._analyse_btn.configure(text='OPTIMIZED', fg_color=self.ACCENT_DARK, text_color=self.ACCENT_GLOW)
        self.app.after(2000, lambda: self._analyse_btn.configure(
            text='ANALYSE DEVICE', fg_color=self.INPUT, text_color=self.ACCENT
        ))

    def _refresh_device_summary(self):
        """Refresh the device summary label from saved profile."""
        try:
            import device_analyzer
            profile = device_analyzer.get_profile()
            if profile:
                gpu = profile.get('gpu_name', 'Unknown')
                if len(gpu) > 24:
                    gpu = gpu[:22] + '...'
                ram = profile.get('ram_gb', '?')
                tier = profile.get('tier', '?')
                self._device_summary.configure(
                    text=f'{tier}  •  {gpu}  •  {ram}GB RAM',
                    text_color=self.TEXT_SEC
                )
            else:
                self._device_summary.configure(
                    text='No profile — click Analyse to optimize',
                    text_color=self.DIM
                )
        except Exception:
            pass

    def _show_model_info(self):
        """Show a popup with all active model and device info."""
        try:
            import device_analyzer
            profile = device_analyzer.get_profile()
        except Exception:
            profile = None

        win = ctk.CTkToplevel(self.app)
        win.title('JARVIS — Model Info')
        win.configure(fg_color=self.BG_DEEP)
        win.resizable(False, False)
        win.attributes('-topmost', True)

        w, h = 380, 420
        x = self.app.winfo_x() + 50
        y = self.app.winfo_y() + 80
        win.geometry(f'{w}x{h}+{x}+{y}')

        # Header
        ctk.CTkLabel(
            win, text='Active Configuration',
            font=ctk.CTkFont(family='Cascadia Code', size=14, weight='bold'),
            text_color=self.ACCENT
        ).pack(pady=(16, 12))

        # Info frame
        info = ctk.CTkFrame(win, fg_color=self.CARD, corner_radius=12)
        info.pack(fill='x', padx=16, pady=(0, 12))

        def _row(parent, label, value, color=None):
            row = ctk.CTkFrame(parent, fg_color='transparent')
            row.pack(fill='x', padx=14, pady=4)
            ctk.CTkLabel(
                row, text=label,
                font=ctk.CTkFont(family='Consolas', size=10, weight='bold'),
                text_color=self.DIM, width=130, anchor='w'
            ).pack(side='left')
            ctk.CTkLabel(
                row, text=str(value),
                font=ctk.CTkFont(family='Consolas', size=11),
                text_color=color or self.TEXT, anchor='w'
            ).pack(side='left', fill='x', expand=True)

        if profile:
            _row(info, 'TIER', profile.get('tier', '—'), self.ACCENT)
            _row(info, 'GPU', profile.get('gpu_name', '—'))
            _row(info, 'VRAM', f"{profile.get('vram_gb', '—')} GB")
            _row(info, 'RAM', f"{profile.get('ram_gb', '—')} GB")
            _row(info, 'CPU CORES', str(profile.get('cpu_cores', '—')))

            ctk.CTkFrame(info, fg_color=self.BORDER, height=1).pack(fill='x', padx=14, pady=6)

            _row(info, 'WHISPER', f"{profile.get('whisper_model', '—')} ({profile.get('compute_type', '—')})")
            _row(info, 'MAIN MODEL', ', '.join(profile.get('preferred_models', ['—'])))
            _row(info, 'LIGHT MODEL', ', '.join(profile.get('lightweight_models', ['—'])))
            vision = profile.get('vision_models', [])
            _row(info, 'VISION', ', '.join(vision) if vision else 'Disabled (CPU)')

            ctk.CTkFrame(info, fg_color=self.BORDER, height=1).pack(fill='x', padx=14, pady=6)

            res = profile.get('capture_resolution', [0, 0])
            _row(info, 'CAPTURE RES', f"{res[0]}x{res[1]}")
            _row(info, 'JPEG QUALITY', str(profile.get('jpeg_quality', '—')))
            _row(info, 'INTERVAL', f"{profile.get('capture_interval', '—')}s")
        else:
            ctk.CTkLabel(
                info, text='\nNo device profile found.\n\nClick "🔍 Analyse Device" first.\n',
                font=ctk.CTkFont(size=12), text_color=self.DIM
            ).pack(pady=16)

        # Spacer at bottom
        ctk.CTkFrame(info, fg_color='transparent', height=8).pack()

        # Close button
        ctk.CTkButton(
            win, text='Close', width=100,
            font=ctk.CTkFont(size=12),
            fg_color=self.INPUT, text_color=self.TEXT_SEC,
            hover_color=self.BORDER, corner_radius=8, height=32,
            command=win.destroy
        ).pack(pady=(0, 16))

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
        self._engine_ready = threading.Event()

        # Show loading state immediately
        self._toggle_btn.configure(
            text='⏳  Loading...',
            fg_color=self.BORDER,
            text_color=self.DIM,
            hover_color=self.BORDER,
            state='disabled'
        )
        self._status_text.configure(text='Starting...', text_color=self.ORANGE)
        self._status_dot.configure(text_color=self.ORANGE)

        # Start loading animation
        self._loading_step = 0
        self._loading_animate()

        # Separate hidden root for ghost overlay
        def _create_ghost():
            self._ghost_root = tk.Toplevel(self.app)
            self._ghost_root.withdraw()
        self.app.after(0, _create_ghost)

        self._engine_thread = threading.Thread(target=self._engine_worker, daemon=True)
        self._engine_thread.start()

        # Poll for engine ready
        self._check_engine_ready()

    def _loading_animate(self):
        """Cycle dots animation on the loading button."""
        if not self._engine_running or self._engine_ready.is_set():
            return
        dots = ['Starting.', 'Starting..', 'Starting...']
        self._toggle_btn.configure(text=dots[self._loading_step % 3])
        self._loading_step += 1
        self._pulse_after = self.app.after(400, self._loading_animate)

    def _check_engine_ready(self):
        """Poll until engine signals ready, then switch to STOP state."""
        if self._engine_ready.is_set():
            self._toggle_btn.configure(
                text='■   STOP JARVIS',
                fg_color=self.RED,
                text_color=self.TEXT,
                hover_color=self.RED_DARK,
                state='normal'
            )
            self._status_text.configure(text='Online', text_color=self.ACCENT)
            self._status_dot.configure(text_color=self.ACCENT)
            self._start_pulse()
            return
        if not self._engine_running:
            return
        self.app.after(200, self._check_engine_ready)

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

        # Cleanup voice engine
        if hasattr(self, '_voice_engine') and self._voice_engine:
            try:
                self._voice_engine.stop()
            except Exception:
                pass
            self._voice_engine = None

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

    def _stop_voice(self):
        """Immediately interrupt TTS."""
        if hasattr(self, '_voice_engine') and self._voice_engine:
            self._voice_engine.stop_speaking()

    def _engine_worker(self):
        try:
            prewarm_ollama()

            # ── Voice Engine ──
            voice = VoiceEngine()
            voice.start()
            self._voice_engine = voice

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
                    self._overlay = GhostOverlay(self._ghost_root)
                except Exception as e:
                    print(f'⚠️  Overlay failed: {e}')
                overlay_ready.set()

            self.app.after(0, _create_overlay)
            overlay_ready.wait(timeout=5)

            # ── OS Controller + Permission Manager ──
            os_ctrl = OSController()
            perm_mgr = PermissionManager(voice_engine=voice, overlay=self._overlay)

            screen = ScreenReader()
            try:
                if self._overlay:
                    screen.set_overlay_hwnd(self._overlay.get_hwnd())
            except Exception:
                pass

            # Hotkey
            if HAS_KEYBOARD:
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
                                voice.speak(sug)
                    except Exception:
                        pass
                try:
                    keyboard.add_hotkey('ctrl+shift+j', on_hotkey, suppress=False)
                    print('🔑 Hotkey active: Ctrl+Shift+J')
                except Exception:
                    pass

            audio = AudioListener()
            
            def on_wake():
                voice.play_beep()
                self.app.after(0, lambda: self._listening_indicator.pack(side='left', padx=(10, 0)))

            audio.set_wake_callback(on_wake)
            audio.start()
            screen.start()
            screen.interval = 4

            import random
            greetings = [
                'Welcome back, sir... How was your day?',
                'Hello again. How can we move forward today, hmm?',
                'I am here, sir. How can I help you right now?',
                'Welcome back. Anything you need me to look at?'
            ]
            voice.speak(random.choice(greetings))
            print('[Core] JARVIS engine started — voice + OS control active')

            # Flush any accidental startup noises from the queue
            while not audio.output_queue.empty():
                try: audio.output_queue.get_nowait()
                except Exception: pass

            # Signal GUI that engine is ready
            self._engine_ready.set()

            while not self._stop_event.is_set():
                try:
                    msg = audio.output_queue.get(timeout=1)
                    if not msg:
                        continue

                    # Hide listening indicator when audio capture finishes
                    self.app.after(0, lambda: self._listening_indicator.pack_forget())

                    # Handle both old string format and new dict format
                    if isinstance(msg, str):
                        msg_type = 'ambient'
                        audio_text = msg
                    else:
                        msg_type = msg.get('type', 'ambient')
                        audio_text = msg.get('text', '')

                    if not audio_text or len(audio_text.strip()) < 3:
                        continue

                    print(f'🎤 [{msg_type}] {audio_text[:80]}')

                    # ── COMMAND MODE ──
                    if msg_type == 'command':
                        cmd = parse_command(audio_text)
                        
                        def _execute_cmd(intent, params, tier, description):
                            result = os_ctrl.execute(intent, params)
                            success = result.get('success', False)
                            message = result.get('message', 'Done')
                            trigger = result.get('action_trigger')
                            log_action(intent, params, 'success' if success else 'failed', tier)

                            if success:
                                voice.speak(message)
                                voice.play_confirm_beep()
                                if self._overlay:
                                    self._overlay.show_popup(f'✅ {message}', description)
                                    
                                if trigger == 'analyze_screen':
                                    import time
                                    time.sleep(1.5)  # Let the browser open and render
                                    sb = screen.get_latest()
                                    if sb:
                                        sug = get_suggestion(
                                            "Read the emails on this screen. Summarize the unread or latest emails concisely. Be warm and professional.",
                                            sb, force_vision=True
                                        )
                                        if sug and sug != 'SILENT':
                                            self._overlay.show_popup(sug, "Email Summary")
                                            voice.speak(sug)
                            else:
                                voice.speak(f'Failed. {message}')
                                voice.play_error_beep()
                                if self._overlay:
                                    self._overlay.show_popup(f'❌ {message}', description)
                            print(f'   → {"✅" if success else "❌"} {message}')

                        if cmd and cmd.intent != 'unknown':
                            # Known command — execute via OS controller
                            description = get_human_description(cmd)
                            print(f'⚡ Command: {cmd.intent} | {description}')
                            perm_mgr.check_permission(
                                intent=cmd.intent,
                                tier=cmd.tier,
                                description=description,
                                on_approved=lambda: _execute_cmd(cmd.intent, cmd.params, cmd.tier, description),
                                on_denied=lambda d=description: voice.speak(f'Cancelled: {d}')
                            )
                        else:
                            # Unknown command — use LLM to interpret
                            response = get_command_response(audio_text)
                            if response:
                                import json
                                import re
                                match = re.search(r'\{.*\}', response, re.DOTALL)
                                if match:
                                    try:
                                        cmd_data = json.loads(match.group(0))
                                        intent = cmd_data.get('intent')
                                        params = cmd_data.get('params', {})
                                        # Default LLM dynamic intents to confirm for safety
                                        tier = cmd_data.get('tier', 'confirm')
                                        if intent:
                                            description = f"AI Command: {intent}"
                                            print(f'⚡ Dynamic Command: {intent} | {params}')
                                            perm_mgr.check_permission(
                                                intent=intent,
                                                tier=tier,
                                                description=description,
                                                on_approved=lambda: _execute_cmd(intent, params, tier, description),
                                                on_denied=lambda d=description: voice.speak('Cancelled AI command')
                                            )
                                            continue
                                    except Exception as e:
                                        print(f"⚠️ Failed to parse AI JSON: {e}")

                                # If no JSON or parsing failed, just speak the response
                                clean_resp = re.sub(r'\{.*\}', '', response, flags=re.DOTALL).strip()
                                if clean_resp:
                                    voice.speak(clean_resp)
                                    if self._overlay:
                                        self._overlay.show_popup(clean_resp, audio_text)
                            print(f'   → LLM: {response[:80] if response else "(empty)"}')

                    # ── AMBIENT MODE ── (existing behavior)
                    else:
                        screen_b64 = screen.get_latest()
                        suggestion = get_suggestion(audio_text, screen_b64)
                        if suggestion and suggestion != 'SILENT':
                            print(f'[AI] Suggestion: {suggestion[:80]}')
                            if self._overlay:
                                self._overlay.show_popup(suggestion, audio_text)
                            voice.speak(suggestion)
                        else:
                            print('   (SILENT)')

                except Exception as e:
                    if not self._stop_event.is_set():
                        # Don't print queue.Empty errors as they happen every second
                        if "Empty" not in str(type(e)):
                            print(f'[Warn] Loop error: {e}')
                    continue

            # Cleanup
            audio.stop()
            screen.stop()
            voice.stop()
            print('[Core] JARVIS engine stopped')

        except Exception as e:
            print(f'[Error] Engine error: {e}')
            import traceback
            traceback.print_exc()
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
        if self._tray:
            try:
                self._tray.stop()
            except Exception:
                pass
        self.app.destroy()
        sys.exit(0)


def launch():
    app = JarvisDashboard()
    app.run()


if __name__ == '__main__':
    launch()
