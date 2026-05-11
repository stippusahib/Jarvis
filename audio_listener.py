# PRIVACY: RAM-only. Zero disk I/O.
import os
import sys

# ── Fix cublas64_12.dll loading ──────────────────────────────────
# CTranslate2 (used by faster-whisper) needs CUDA libs on the DLL
# search path.  Add common CUDA locations before any CUDA import.
def _add_cuda_dll_paths():
    """Add CUDA toolkit bin directories to DLL search path."""
    cuda_paths = []

    # 1. CUDA_PATH env var (set by NVIDIA installer)
    cuda_home = os.environ.get('CUDA_PATH') or os.environ.get('CUDA_HOME', '')
    if cuda_home:
        cuda_paths.append(os.path.join(cuda_home, 'bin'))

    # 2. Common NVIDIA toolkit install directories
    for ver in ('12.9', '12.8', '12.6', '12.4', '12.3', '12.2', '12.1', '12.0'):
        cuda_paths.append(rf'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v{ver}\bin')

    # 3. Scan site-packages/nvidia/*/bin directly
    #    PEP 420 namespace packages (nvidia.*) have __file__ = None on
    #    Python 3.14+, so __import__ + dirname fails. Instead, walk
    #    site-packages to find the actual DLL directories.
    for sp in sys.path:
        nvidia_root = os.path.join(sp, 'nvidia')
        if os.path.isdir(nvidia_root):
            try:
                for subpkg in os.listdir(nvidia_root):
                    for sub in ('bin', 'lib'):
                        candidate = os.path.join(nvidia_root, subpkg, sub)
                        if os.path.isdir(candidate):
                            cuda_paths.append(candidate)
            except OSError:
                pass

    # 4. PyTorch bundled CUDA libs (fallback)
    try:
        import torch
        torch_lib = os.path.join(os.path.dirname(torch.__file__), 'lib')
        if os.path.isdir(torch_lib):
            cuda_paths.append(torch_lib)
    except Exception:
        pass

    added = []
    for path in cuda_paths:
        if os.path.isdir(path) and path not in added:
            added.append(path)
            os.environ['PATH'] = path + os.pathsep + os.environ.get('PATH', '')
            try:
                os.add_dll_directory(path)
            except (OSError, AttributeError):
                pass

_add_cuda_dll_paths()
# ─────────────────────────────────────────────────────────────────

import sounddevice as sd
import gc
import threading
import queue
import time
import difflib
import numpy as np

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

try:
    import noisereduce as nr
    HAS_NOISEREDUCE = True
except ImportError:
    HAS_NOISEREDUCE = False

from faster_whisper import WhisperModel


class AudioListener:
    """Captures mic audio, transcribes with Whisper, and outputs text to a queue.
    
    Outputs tagged messages: {type: 'command'|'ambient', text: '...'}
    Command mode: after wake word, captures next 8s as dedicated command.
    """

    @staticmethod
    def _load_wake_words():
        """Load wake words from settings AND keep defaults alive."""
        base_words = ["jarvis", "hey jarvis", "ok jarvis", "yo jarvis"]
        try:
            import settings_manager
            custom = settings_manager.get('wake_words', [])
            words = list(set(base_words + custom))
            
            # Also add user name
            name = settings_manager.get('user_name', '')
            if name and name.lower() not in words:
                words.append(name.lower())
            return words
        except Exception:
            return base_words

    WAKE_WORDS = _load_wake_words()

    RATE = 16000
    CHUNK = 1024
    CHANNELS = 1
    RECORD_SECONDS = 5
    COMMAND_RECORD_SECONDS = 8  # Longer capture for command mode

    def __init__(self):
        # Load device profile for optimal settings
        try:
            import settings_manager
            profile = settings_manager.get('device_profile', {})
            whisper_model = profile.get('whisper_model', 'small')
            compute_type = profile.get('compute_type', None)
        except Exception:
            whisper_model = 'small'
            compute_type = None

        # Ensure downloads are enabled (remove ALL offline flags)
        import os
        os.environ.pop('HF_HUB_OFFLINE', None)
        os.environ.pop('TRANSFORMERS_OFFLINE', None)
        os.environ['HF_HUB_OFFLINE'] = '0'

        # CUDA auto-detection
        # CTranslate2 handles CUDA internally, so we don't need PyTorch to check it.
        # Just try CUDA first, and if it fails, the exception handler will fall back.
        device = "cuda"
        if compute_type is None:
            compute_type = "float16"

        # Load Whisper with fallback chain
        fallback_chain = [whisper_model, 'small', 'base', 'tiny']
        # Remove duplicates while preserving order
        seen = set()
        models_to_try = []
        for m in fallback_chain:
            if m not in seen:
                seen.add(m)
                models_to_try.append(m)

        self.model = None
        for model_name in models_to_try:
            try:
                self.model = WhisperModel(model_name, device=device, compute_type=compute_type)
                print(f"[Whisper] Loaded: {model_name} on {device.upper()} ({compute_type})")
                break
            except Exception as e:
                print(f"[Whisper] {model_name} on {device} failed: {e}")
                # Retry with CUDA int8
                try:
                    self.model = WhisperModel(model_name, device=device, compute_type='int8')
                    print(f"[Whisper] Loaded: {model_name} on {device.upper()} (int8 fallback)")
                    break
                except Exception:
                    pass
                    
                # If CUDA totally fails, retry with CPU int8
                try:
                    self.model = WhisperModel(model_name, device='cpu', compute_type='int8')
                    print(f"[Whisper] Loaded: {model_name} on CPU (int8 fallback)")
                    break
                except Exception:
                    continue

        if self.model is None:
            raise RuntimeError("Could not load any Whisper model. Check your internet connection.")

        # Lock offline mode — all models are loaded, no more network needed
        os.environ['HF_HUB_OFFLINE'] = '1'
        os.environ['TRANSFORMERS_OFFLINE'] = '1'

        self.output_queue = queue.Queue()
        self.running = False
        self.last_text = ""
        self.last_text_time = 0.0
        self._command_mode = False
        self._on_wake_callback = None  # Called when wake word detected (for beep)

        # Mic device auto-selection: Prefer headsets/headphones over array
        self._mic_index = None
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            best_mic = None
            default_mic = None
            
            try:
                default_info = sd.query_devices(kind='input')
                default_mic = default_info["name"]
            except Exception:
                pass

            # Search for headset explicitly
            for i, dev in enumerate(devices):
                if dev.get('max_input_channels', 0) > 0:
                    name = dev.get('name', '').lower()
                    if 'headset' in name or 'bluetooth' in name or 'headphones' in name:
                        best_mic = dev['name']
                        break
                        
            self._mic_index = best_mic if best_mic else default_mic
            
            if self._mic_index:
                print(f"[Mic] Selected: {self._mic_index}")
            else:
                print("[Mic] Using system default")
        except Exception:
            self._mic_index = None  # sounddevice will use system default
            print("[Mic] Using system default")

    def set_wake_callback(self, callback):
        """Set callback for when wake word is detected (e.g. play beep)."""
        self._on_wake_callback = callback

    def start(self):
        """Start listening in a background daemon thread."""
        self.running = True
        t = threading.Thread(target=self._capture_loop, daemon=True)
        t.start()

    def _capture_loop(self):
        """Main capture loop — records, transcribes, debounces, and queues text."""
        while self.running:
            try:
                num_frames = int(self.RATE * self.RECORD_SECONDS)
                audio_array = sd.rec(num_frames, samplerate=self.RATE, channels=self.CHANNELS, dtype='float32', device=self._mic_index)
                sd.wait()

                if not self.running:
                    break

                # Convert to numpy 1D array
                audio_array = audio_array.flatten()

                # Audio Pre-processing: Apply noise reduction
                # Treat the first 0.5s as a noise profile if possible, or just apply stationary reduction
                if HAS_NOISEREDUCE:
                    audio_array = nr.reduce_noise(y=audio_array, sr=self.RATE, prop_decrease=0.8, stationary=True)

                # Check audio energy — skip silent frames before calling Whisper
                energy = float(np.abs(audio_array).mean())
                if energy < 0.001:
                    del audio_array
                    gc.collect()
                    continue

                # Prompting / Custom Glossary: inject context
                custom_prompt = "Alfie, Tippu, Stippu, file, document, code, architecture, plan, JARVIS, summary, project, meeting."

                # Transcribe with Whisper — vad_filter=False to keep short speech
                segments, info = self.model.transcribe(
                    audio_array, 
                    language="en", 
                    vad_filter=False,
                    initial_prompt=custom_prompt
                )
                
                # Confidence Filtering: Only use segments with high probability
                valid_segments = []
                for s in segments:
                    # avg_logprob is log probability. e^-0.35 is ~0.70 confidence (70%)
                    # no_speech_prob is probability the segment is just noise/silence
                    if s.no_speech_prob < 0.8:
                        valid_segments.append(s.text)
                
                text = " ".join(valid_segments).strip()

                # Debounce check
                if text and len(text) > 15:
                    # Hallucination filter — reject transcriptions with fake/nonsense words
                    common_real_words = set([
                        "the", "and", "for", "you", "that", "this", "with", "have",
                        "file", "code", "loop", "data", "read", "sent", "plan", "check",
                        "slow", "fast", "error", "function", "meeting", "project", "did",
                        "nested", "running", "looking", "working", "trying", "need", "know",
                        "think", "said", "your", "our", "can", "will", "should", "would",
                        "alfie", "tippu", "hey", "did", "read", "send", "share", "open",
                        "jarvis", "fix", "help", "what", "why", "how", "time", "check"
                    ])
                    text_words = set(text.lower().split())
                    real_word_count = len(text_words.intersection(common_real_words))
                    total_words = len(text_words)
                    if total_words > 3 and real_word_count == 0:
                        # Zero real words = pure hallucination, skip
                        del audio_array
                        gc.collect()
                        continue

                    # Wake word detection — enhance if JARVIS is addressed
                    text_lower = text.lower()
                    has_wake_word = any(wake in text_lower for wake in self.WAKE_WORDS)

                    if has_wake_word:
                        # Strip wake word from text before sending to LLM
                        cleaned = text_lower
                        for wake in sorted(self.WAKE_WORDS, key=len, reverse=True):
                            cleaned = cleaned.replace(wake, "").strip()
                        # Use cleaned text if meaningful, else original
                        if len(cleaned) > 3:
                            text = cleaned

                        # Signal wake word detected
                        if self._on_wake_callback:
                            try:
                                self._on_wake_callback()
                            except Exception:
                                pass

                        # If command has content, send as command type
                        if len(text.strip()) > 3:
                            self.output_queue.put({"type": "command", "text": text})
                            self.last_text = text
                            self.last_text_time = time.time()
                        else:
                            # Wake word only — enter command mode for next capture
                            self._command_mode = True
                            print("🎤 Wake word detected — listening for command...")

                        del audio_array
                        gc.collect()
                        continue

                    # Command mode — this block is a follow-up command
                    if self._command_mode:
                        self._command_mode = False
                        if len(text.strip()) > 3:
                            self.output_queue.put({"type": "command", "text": text})
                            self.last_text = text
                            self.last_text_time = time.time()
                        del audio_array
                        gc.collect()
                        continue

                    # Normal ambient mode — debounce and queue
                    current_time = time.time()
                    if current_time - self.last_text_time > 12:
                        self.last_text = ""

                    ratio = difflib.SequenceMatcher(None, self.last_text, text).ratio()
                    if ratio < 0.7:
                        self.output_queue.put({"type": "ambient", "text": text})
                        self.last_text = text
                        self.last_text_time = current_time

                del audio_array
                gc.collect()

            except OSError:
                print("[Warn] Mic error. Retrying in 2s...")
                time.sleep(2)
                continue
            except Exception as e:
                print(f"[Warn] Audio error: {e}")
                continue
            finally:
                pass

    def stop(self):
        """Stop listening and release PyAudio."""
        self.running = False
        try:
            sd.stop()
        except Exception:
            pass
