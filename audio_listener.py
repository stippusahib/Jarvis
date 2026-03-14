# PRIVACY: RAM-only. Zero disk I/O.
import pyaudio
import io
import gc
import threading
import queue
import time
import difflib
import numpy as np
import scipy.io.wavfile as wavfile
import io

try:
    import noisereduce as nr
    HAS_NOISEREDUCE = True
except ImportError:
    HAS_NOISEREDUCE = False

from faster_whisper import WhisperModel


class AudioListener:
    """Captures mic audio, transcribes with Whisper, and outputs text to a queue."""

    RATE = 16000
    CHUNK = 1024
    CHANNELS = 1
    FORMAT = pyaudio.paInt16
    RECORD_SECONDS = 5

    def __init__(self):
        # CUDA auto-detection
        try:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            compute = "float16" if device == "cuda" else "int8"
        except ImportError:
            device = "cpu"
            compute = "int8"

        self.model = WhisperModel("small", device=device, compute_type=compute)
        print(f"🎙️  Whisper loaded on: {device.upper()}")

        self.output_queue = queue.Queue()
        self.running = False
        self.last_text = ""
        self.last_text_time = 0.0

        # Mic device auto-selection
        self._pa = pyaudio.PyAudio()
        self._mic_index = None
        try:
            default_info = self._pa.get_default_input_device_info()
            self._mic_index = default_info["index"]
            print(f"🎤 Mic selected: {default_info['name']} (index {self._mic_index})")
        except Exception:
            self._mic_index = None  # PyAudio will use system default
            print("🎤 Mic: using system default")

    def start(self):
        """Start listening in a background daemon thread."""
        self.running = True
        t = threading.Thread(target=self._capture_loop, daemon=True)
        t.start()

    def _capture_loop(self):
        """Main capture loop — records, transcribes, debounces, and queues text."""
        while self.running:
            stream = None
            try:
                stream = self._pa.open(
                    format=self.FORMAT,
                    channels=self.CHANNELS,
                    rate=self.RATE,
                    input=True,
                    frames_per_buffer=self.CHUNK,
                    input_device_index=self._mic_index,
                )

                frames = []
                num_frames = int(self.RATE / self.CHUNK * self.RECORD_SECONDS)
                for _ in range(num_frames):
                    if not self.running:
                        break
                    data = stream.read(self.CHUNK, exception_on_overflow=False)
                    frames.append(data)

                stream.stop_stream()
                stream.close()
                stream = None

                if not frames:
                    continue

                # Convert to numpy float32 array
                audio_array = np.frombuffer(b"".join(frames), dtype=np.int16).astype(np.float32) / 32768.0

                # Audio Pre-processing: Apply noise reduction
                # Treat the first 0.5s as a noise profile if possible, or just apply stationary reduction
                if HAS_NOISEREDUCE:
                    audio_array = nr.reduce_noise(y=audio_array, sr=self.RATE, prop_decrease=0.8, stationary=True)

                # Check audio energy — skip silent frames before calling Whisper
                energy = float(np.abs(audio_array).mean())
                if energy < 0.001:
                    del audio_array, frames
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
                if text and len(text) > 18:
                    # Hallucination filter — reject transcriptions with fake/nonsense words
                    common_real_words = set([
                        "the", "and", "for", "you", "that", "this", "with", "have",
                        "file", "code", "loop", "data", "read", "sent", "plan", "check",
                        "slow", "fast", "error", "function", "meeting", "project", "did",
                        "nested", "running", "looking", "working", "trying", "need", "know",
                        "think", "said", "your", "our", "can", "will", "should", "would",
                        "alfie", "tippu", "hey", "did", "read", "send", "share", "open"
                    ])
                    text_words = set(text.lower().split())
                    real_word_count = len(text_words.intersection(common_real_words))
                    total_words = len(text_words)
                    if total_words > 3 and real_word_count == 0:
                        # Zero real words = pure hallucination, skip
                        del audio_array, frames
                        gc.collect()
                        continue

                    # Auto-reset debounce after 15 seconds — new topic always passes
                    current_time = time.time()
                    if current_time - self.last_text_time > 15:
                        self.last_text = ""

                    ratio = difflib.SequenceMatcher(None, self.last_text, text).ratio()
                    if ratio < 0.7:
                        self.output_queue.put(text)
                        self.last_text = text
                        self.last_text_time = current_time

                del audio_array, frames
                gc.collect()

            except OSError:
                print("⚠️  Mic error. Retrying in 2s...")
                time.sleep(2)
                continue
            except Exception as e:
                print(f"⚠️  Audio error: {e}")
                continue
            finally:
                if stream is not None:
                    try:
                        stream.stop_stream()
                        stream.close()
                    except Exception:
                        pass

    def stop(self):
        """Stop listening and release PyAudio."""
        self.running = False
        try:
            self._pa.terminate()
        except Exception:
            pass
