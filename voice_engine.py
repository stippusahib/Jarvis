# JARVIS Voice Engine — Natural, expressive TTS with edge-tts.
# Primary: edge-tts (Microsoft neural voices — warm, human female).
# Fallback: pyttsx3 (offline, robotic but functional).
# PRIVACY: Audio is generated via Microsoft Edge TTS (text sent to MS servers).
#          Only JARVIS response text is sent — never mic audio or screen data.
import threading
import queue
import asyncio
import tempfile
import os
import re
import time


# ─── Emotion Detection ───────────────────────────────────────────────
# Maps keywords in JARVIS responses to SSML emotion styles.
EMOTION_MAP = {
    'cheerful': [
        'done', 'sure', 'great', 'awesome', 'perfect', 'absolutely',
        'happy', 'love', 'wonderful', 'excellent', 'nice', 'cool',
        'opened', 'launched', 'started', 'playing', 'success',
        'online', 'operational', 'ready', 'activated',
    ],
    'empathetic': [
        'sorry', 'failed', 'error', 'couldn\'t', 'can\'t', 'unable',
        'unfortunately', 'problem', 'issue', 'wrong', 'broken',
        'cancelled', 'denied', 'not found', 'missing',
    ],
    'gentle': [
        'suggestion', 'consider', 'perhaps', 'might', 'maybe',
        'notice', 'quiet', 'silent', 'watching', 'listening',
    ],
    'whispering': [
        'goodnight', 'sleep', 'relax', 'calm', 'shh', 'secret',
        'between us', 'just for you', 'softly',
    ],
}


def _detect_emotion(text: str) -> str:
    """Detect emotion from response text using keyword matching."""
    text_lower = text.lower()
    scores = {}
    for emotion, keywords in EMOTION_MAP.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[emotion] = score

    if scores:
        return max(scores, key=scores.get)
    return 'chat'  # intimate, casual default — warmest baseline


# ─── SSML Builder ─────────────────────────────────────────────────────
VOICE_NAME = 'en-US-JennyNeural'


def _humanize_text(text: str) -> str:
    """Insert SSML break tags at natural pause points for human-like rhythm.

    Real people pause after commas, breathe between sentences, and
    linger slightly on dashes. This function injects those micro-pauses.
    """
    import re

    # Pause after sentences (period, exclamation, question mark)
    text = re.sub(r'([.!?])\s+', r'\1 <break time="350ms"/> ', text)

    # Shorter pause after commas
    text = re.sub(r',\s+', r', <break time="180ms"/> ', text)

    # Pause around dashes (— or --)
    text = re.sub(r'\s*[—–]\s*', ' <break time="250ms"/> ', text)
    text = re.sub(r'\s*--\s*', ' <break time="250ms"/> ', text)

    # Pause for ellipsis (thinking feel)
    text = re.sub(r'\.{2,}', '<break time="400ms"/>', text)

    # Slight pause after colons and semicolons
    text = re.sub(r'[:;]\s+', r': <break time="200ms"/> ', text)

    return text


def _build_ssml(text: str, emotion: str) -> str:
    """Build SSML with emotion, pitch, prosody, and natural pauses."""
    # Escape XML special characters FIRST
    safe_text = (
        text.replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&apos;')
    )

    # Then inject natural pauses
    humanized = _humanize_text(safe_text)

    return (
        f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
        f'xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="en-US">'
        f'<voice name="{VOICE_NAME}">'
        f'<mstts:express-as style="{emotion}" styledegree="1.0">'
        f'{humanized}'
        f'</mstts:express-as>'
        f'</voice>'
        f'</speak>'
    )


class VoiceEngine:
    """Expressive TTS engine — JARVIS speaks with a warm, natural female voice.

    Features:
    - edge-tts: Natural Microsoft neural voice with emotion
    - Fallback: pyttsx3 when offline
    - Non-blocking: speaks in background thread
    - Queue-based: new speech auto-queues
    - Interruptible: can cancel current speech
    - Configurable: speed, volume, voice from settings
    """

    def __init__(self):
        self._queue = queue.Queue()
        self._running = False
        self._thread = None
        self._speaking = False
        self._stop_current = False
        self._enabled = True
        self._speed = '+0%'       # Standard speed
        self._volume = '+0%'      # Standard volume
        self._pitch = '+0%'       # Standard pitch
        self._voice_id = 'en-US-JennyNeural'

        # Fallback engine (pyttsx3)
        self._fallback_engine = None
        self._use_fallback = False

        # Track temp file for cleanup
        self._current_temp = None

        # Load settings
        try:
            import settings_manager
            self._enabled = settings_manager.get('voice_enabled', True)
            pyttsx3_speed = settings_manager.get('voice_speed', 175)
            pyttsx3_volume = settings_manager.get('voice_volume', 0.9)

            # Convert pyttsx3 speed (175 WPM) to edge-tts rate percentage
            # 175 is default, so 200 → +14%, 150 → -14%
            rate_pct = int(((pyttsx3_speed - 175) / 175) * 100)
            self._speed = f'{rate_pct:+d}%'

            # Convert 0.0-1.0 volume to edge-tts percentage
            vol_pct = int((pyttsx3_volume - 1.0) * 100)
            self._volume = f'{vol_pct:+d}%'

        except Exception:
            pass

    def start(self):
        """Start the voice engine background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()
        print("[TTS] Voice engine started (edge-tts neural)")

    def _init_fallback(self):
        """Initialize pyttsx3 as offline fallback."""
        try:
            import pyttsx3
            self._fallback_engine = pyttsx3.init()
            self._fallback_engine.setProperty('rate', 175)
            self._fallback_engine.setProperty('volume', 0.9)
            # Try to pick Zira (female) for consistency
            voices = self._fallback_engine.getProperty('voices')
            for v in voices:
                if 'zira' in v.name.lower():
                    self._fallback_engine.setProperty('voice', v.id)
                    break
            print("[TTS] Fallback TTS (pyttsx3) ready")
            return True
        except Exception as e:
            print(f"[TTS] Fallback TTS unavailable: {e}")
            return False

    def _worker(self):
        """Background worker that processes the speech queue."""
        # Create a dedicated event loop for async edge-tts calls
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Pre-init fallback so it's ready if needed
        self._init_fallback()

        while self._running:
            try:
                text = self._queue.get(timeout=0.5)
                if text is None:
                    continue
                if not self._enabled:
                    continue

                self._speaking = True
                self._stop_current = False

                try:
                    # Clean text for speech
                    clean = self._clean_for_speech(text)
                    if not clean:
                        continue

                    # Detect emotion from text content
                    emotion = _detect_emotion(clean)

                    # Try edge-tts first
                    if not self._use_fallback:
                        try:
                            loop.run_until_complete(
                                self._speak_edge(clean, emotion)
                            )
                            continue  # Success — skip fallback
                        except Exception as e:
                            print(f"[TTS] edge-tts failed ({e}) -- using fallback for this message only")

                    # Fallback to pyttsx3
                    if self._fallback_engine and not self._stop_current:
                        try:
                            self._fallback_engine.say(clean)
                            self._fallback_engine.runAndWait()
                        except Exception as e:
                            print(f"[TTS] Fallback TTS error: {e}")

                except Exception as e:
                    print(f"[TTS] error: {e}")
                finally:
                    self._speaking = False
                    self._cleanup_temp()

            except queue.Empty:
                continue
            except Exception:
                continue

        loop.close()

    async def _speak_edge(self, text: str, emotion: str):
        """Generate speech with edge-tts and play via Windows MCI."""
        import ssl
        import aiohttp
        import edge_tts
        import edge_tts.communicate

        if self._stop_current:
            return

        # ── SSL bypass for corporate/VPN proxies with self-signed certs ──
        # Patch aiohttp so edge-tts's internal ClientSession uses ssl=False.
        # This only affects this process — no system certs are modified.
        if not hasattr(aiohttp, '_jarvis_ssl_patched'):
            _ssl_ctx = ssl.create_default_context()
            _ssl_ctx.check_hostname = False
            _ssl_ctx.verify_mode = ssl.CERT_NONE
            _orig_connector_init = aiohttp.TCPConnector.__init__

            def _patched_connector_init(self_, *args, **kwargs):
                kwargs.setdefault('ssl', _ssl_ctx)
                _orig_connector_init(self_, *args, **kwargs)

            aiohttp.TCPConnector.__init__ = _patched_connector_init
            aiohttp._jarvis_ssl_patched = True
        # ─────────────────────────────────────────────────────────────────

        # Monkeypatch edge_tts to allow raw SSML, so it doesn't literally say "<speak version="
        if not hasattr(edge_tts.communicate, '_jarvis_patched'):
            _orig_escape = edge_tts.communicate.escape
            _orig_mkssml = edge_tts.communicate.mkssml

            def _custom_escape(t):
                if t.startswith("<speak version"): return t
                return _orig_escape(t)

            def _custom_mkssml(tc, escaped_text):
                if isinstance(escaped_text, bytes):
                    escaped_text = escaped_text.decode("utf-8")
                if escaped_text.startswith("<speak version"):
                    return escaped_text
                return _orig_mkssml(tc, escaped_text)

            edge_tts.communicate.escape = _custom_escape
            edge_tts.communicate.mkssml = _custom_mkssml
            edge_tts.communicate._jarvis_patched = True

        # Build SSML with emotion
        ssml = _build_ssml(text, emotion)

        # Generate to temp file (in-memory would be ideal but MCI needs a file)
        tmp = tempfile.NamedTemporaryFile(
            suffix='.mp3', delete=False, prefix='jarvis_tts_'
        )
        tmp_path = tmp.name
        tmp.close()
        self._current_temp = tmp_path

        try:
            # Try SSML first, fall back to plain text if SSML fails
            try:
                communicate = edge_tts.Communicate(
                    ssml,
                    voice=self._voice_id,
                    rate=self._speed,
                    volume=self._volume
                )
                await communicate.save(tmp_path)
            except Exception:
                # SSML might not be supported — use plain text
                communicate = edge_tts.Communicate(
                    text,
                    voice=self._voice_id,
                    rate=self._speed,
                    volume=self._volume
                )
                await communicate.save(tmp_path)

            if self._stop_current:
                return

            # Play via Windows MCI (built-in, no extra deps)
            self._play_audio_mci(tmp_path)

        except Exception as e:
            raise e

    def _play_audio_mci(self, filepath: str):
        """Play MP3 using Windows MCI (winmm.dll) — zero dependencies."""
        import ctypes

        winmm = ctypes.windll.winmm  # type: ignore
        mci_send = winmm.mciSendStringW

        # Escape backslashes in path
        safe_path = filepath.replace('\\', '\\\\')

        # Open the audio file
        mci_send(f'open "{safe_path}" type mpegvideo alias jarvis_voice', 0, 0, 0)

        # Play it
        mci_send('play jarvis_voice', 0, 0, 0)

        # Wait for playback to finish (poll status)
        status_buf = ctypes.create_unicode_buffer(128)
        while not self._stop_current:
            mci_send('status jarvis_voice mode', status_buf, 128, 0)
            mode = status_buf.value
            if mode != 'playing':
                break
            time.sleep(0.05)

        # Stop and close
        mci_send('stop jarvis_voice', 0, 0, 0)
        mci_send('close jarvis_voice', 0, 0, 0)

    def _cleanup_temp(self):
        """Remove temp audio file if it exists."""
        if self._current_temp:
            try:
                os.unlink(self._current_temp)
            except Exception:
                pass
            self._current_temp = None

    def _clean_for_speech(self, text: str) -> str:
        """Clean text for natural speech — remove emojis, formatting, etc."""
        if not text:
            return ""

        clean = text.strip()

        # Remove emoji characters
        clean = re.sub(
            r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF'
            r'\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF'
            r'\U00002702-\U000027B0\U000024C2-\U0001F251'
            r'\u2640-\u2642\u2600-\u2B55\u200d\u23cf'
            r'\u23e9\u231a\ufe0f\u3030\u2328⚡●■▶⏳🔍💾✕⟲]+',
            '', clean
        )

        # Remove markdown formatting
        clean = re.sub(r'[*_~`#]', '', clean)
        clean = clean.replace('ISSUE:', '').replace('FIX:', '')
        # Collapse whitespace
        clean = re.sub(r'\s+', ' ', clean).strip()

        return clean

    def speak(self, text: str):
        """Queue text for speech (non-blocking)."""
        if not self._enabled or not self._running:
            return
        # Clear pending — only latest matters
        self._clear_queue()
        self._queue.put(text)

    def speak_async(self, text: str):
        """Same as speak() — kept for API compatibility."""
        self.speak(text)

    def speak_and_wait(self, text: str, timeout: float = 15.0):
        """Speak and block until done (with timeout)."""
        if not self._enabled or not self._running:
            return
        self._clear_queue()
        self._queue.put(text)
        start = time.time()
        time.sleep(0.5)  # Let worker pick it up
        while self._speaking and (time.time() - start) < timeout:
            time.sleep(0.1)

    def stop_speaking(self):
        """Stop current speech immediately."""
        self._stop_current = True
        self._clear_queue()

        # Stop MCI playback immediately
        try:
            import ctypes
            winmm = ctypes.windll.winmm  # type: ignore
            winmm.mciSendStringW('stop jarvis_voice', 0, 0, 0)
            winmm.mciSendStringW('close jarvis_voice', 0, 0, 0)
        except Exception:
            pass

        # Also stop pyttsx3 if active
        if self._fallback_engine and self._speaking:
            try:
                self._fallback_engine.stop()
            except Exception:
                pass

    def _clear_queue(self):
        """Drain the queue."""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

    @property
    def is_speaking(self) -> bool:
        return self._speaking

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool):
        self._enabled = enabled
        if not enabled:
            self.stop_speaking()

    def set_speed(self, speed: int):
        """Set speech speed (WPM-style). Converts to edge-tts rate %."""
        rate_pct = int(((speed - 175) / 175) * 100)
        self._speed = f'{rate_pct:+d}%'

    def set_volume(self, volume: float):
        """Set volume (0.0 to 1.0)."""
        volume = max(0.0, min(1.0, volume))
        vol_pct = int((volume - 1.0) * 100)
        self._volume = f'{vol_pct:+d}%'

    def set_voice(self, voice_id: str):
        """Set voice by edge-tts voice name."""
        self._voice_id = voice_id

    def get_available_voices(self) -> list:
        """Return list of available edge-tts voices (async, cached)."""
        try:
            import edge_tts
            loop = asyncio.new_event_loop()
            voices = loop.run_until_complete(edge_tts.list_voices())
            loop.close()
            # Filter to English female voices
            result = []
            for v in voices:
                if v.get('Locale', '').startswith('en') and v.get('Gender') == 'Female':
                    result.append((v['ShortName'], v['FriendlyName']))
            return result
        except Exception:
            return []

    def play_beep(self):
        """Play a short beep to indicate JARVIS is listening."""
        pass

    def play_confirm_beep(self):
        """Play a confirmation beep (two-tone)."""
        pass

    def play_error_beep(self):
        """Play an error beep (descending)."""
        pass

    def stop(self):
        """Shutdown the voice engine."""
        self._running = False
        self.stop_speaking()
        self._clear_queue()
        self._cleanup_temp()
        if self._fallback_engine:
            try:
                self._fallback_engine.stop()
            except Exception:
                pass
        print("[TTS] Voice engine stopped")
