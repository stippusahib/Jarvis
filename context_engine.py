# PRIVACY: RAM-only. Zero disk I/O.
import requests
import gc
import time
import threading
import ctypes
import platform
import psutil

try:
    import pygetwindow as gw
    HAS_PYGETWINDOW = True
except ImportError:
    HAS_PYGETWINDOW = False

from file_scout import is_file_mention, find_recent_file
from file_reader import read_file_context

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
OLLAMA_TAGS_URL = "http://127.0.0.1:11434/api/tags"
PREFERRED_MODELS = ["mistral", "llama3.2"]
LIGHTWEIGHT_MODELS = ["phi3:mini", "tinyllama"]
_active_model_main = None
_active_model_light = None
_model_lock = threading.Lock()

# -----------------------------------------------------------------------------
# OS SPECIFIC DEFINITIONS
# -----------------------------------------------------------------------------
if platform.system() == "Windows":
    class SYSTEM_POWER_STATUS(ctypes.Structure):
        _fields_ = [
            ("ACLineStatus", ctypes.c_byte),
            ("BatteryFlag", ctypes.c_byte),
            ("BatteryLifePercent", ctypes.c_byte),
            ("SystemStatusFlag", ctypes.c_byte),
            ("BatteryLifeTime", ctypes.c_ulong),
            ("BatteryFullLifeTime", ctypes.c_ulong)
        ]
else:
    class SYSTEM_POWER_STATUS:
        # Placeholder for non-Windows systems
        pass

# -----------------------------------------------------------------------------
# SESSION LEARNING (RAM ONLY)
# -----------------------------------------------------------------------------
# This stores keywords/concepts the user thumbs-ups or thumbs-downs.
# Wiped cleanly when the process dies.
session_preferences = {
    "likes": [],
    "dislikes": []
}

def _extract_text_content(lines: list, max_words=100) -> str:
    """Helper to safely extract specific number of words from a string list."""
    if not lines:
        return ""
    full_text = " ".join(lines)
    words = full_text.split()
    return " ".join(words[:max_words])

def record_feedback(text: str, score: int):
    """Analyze the text and store broad keywords in RAM only."""
    # Extremely basic stopword removal to find key concepts
    stopwords = {"the","is","in","at","of","on","and","a","to","it","for","with","this","that","you","are"}
    words = [w.lower().strip(".,!?()") for w in text.split() if w.lower() not in stopwords]
    
    # Store top 3 longest words as rough concepts
    concepts = sorted(words, key=len, reverse=True)[:3]
    
    if score > 0:
        session_preferences["likes"].extend(concepts)
        print(f"📈 Learned positive preference: {concepts}")
    else:
        session_preferences["dislikes"].extend(concepts)
        print(f"📉 Learned negative preference: {concepts}")

    # Keep list from growing infinitely, ensuring it's always a list
    session_preferences["likes"] = list(set(session_preferences["likes"]))[-15:]
    session_preferences["dislikes"] = list(set(session_preferences["dislikes"]))[-15:]

# -----------------------------------------------------------------------------
# CORE LOGIC
# -----------------------------------------------------------------------------
def is_battery_saver_on() -> bool:
    if platform.system() != "Windows":
        return False
        
    try:
        status = SYSTEM_POWER_STATUS()
        if hasattr(ctypes, 'windll'):
            res = ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status))
            if res:
                # SystemStatusFlag bit 0 is battery saver
                return bool(status.SystemStatusFlag & 1)
    except Exception as e:
        print(f"Power check failed: {e}")
    return False

SYSTEM_PROMPT = """You are JARVIS — a silent ambient AI assistant running fully offline on the user's device.
You perceive their screen and hear what they say in real-time.

Your ONLY job: whisper ONE hyper-specific, immediately useful suggestion in 15 words or fewer.

Context detection — adapt your suggestion style:
- If user is CODING: suggest performance fixes, bugs, or patterns
- If user is in a MEETING: suggest social cues, names, action items
- If user is WRITING: suggest clarity, missing points, or next steps
- If user is BROWSING: suggest related concepts worth knowing now

Rules:
- Never ask questions
- Never give generic advice
- Only respond if something SPECIFIC and ACTIONABLE applies right now
- If nothing useful: respond with exactly the word SILENT and nothing else
- 15 words maximum. Sound like a genius friend whispering, not a chatbot.

Good examples:
"That nested loop is O(n²) — a dict lookup cuts it to O(1)."
"John just said your name — unmute now."
"Priya asked a direct question 3 messages ago — still unread."
"GDPR Article 17 covers this — right to erasure applies here."
"This function has no error handling — add a try/except before demo."
"""


def detect_available_models():
    """Query Ollama for available models and pick the best main and lightweight models."""
    try:
        response = requests.get(OLLAMA_TAGS_URL, timeout=5)
        response.raise_for_status()
        data = response.json()
        available = data.get("models", [])
        
        main_model = None
        for preferred in PREFERRED_MODELS:
            for model in available:
                model_name = model.get("name", "")
                if preferred in model_name:
                    main_model = model_name
                    break
            if main_model: break
            
        light_model = None
        for preferred in LIGHTWEIGHT_MODELS:
            for model in available:
                model_name = model.get("name", "")
                if preferred in model_name:
                    light_model = model_name
                    break
            if light_model: break
            
        return main_model, light_model
    except Exception:
        pass
    return None, None


def prewarm_ollama():
    """Pre-warm Ollama at startup so first real suggestion is fast."""
    global _active_model_main, _active_model_light
    main_model, light_model = detect_available_models()
    with _model_lock:
        _active_model_main = main_model
        _active_model_light = light_model

    if _active_model_main:
        try:
            requests.post(OLLAMA_URL, json={
                "model": _active_model_main,
                "messages": [{"role": "user", "content": "hi"}],
                "stream": False,
                "options": {"num_predict": 1}
            }, timeout=15)
            print(f"✅ Ollama ready — main model: {_active_model_main}")
            if _active_model_light:
                print(f"🔋 Lightweight model available for battery saver: {_active_model_light}")
        except Exception:
            print("⚠️  Ollama pre-warm failed — first suggestion may be slow")
    else:
        print("⚠️  Ollama not reachable. Run: ollama serve")


def get_suggestion(audio_text, screen_b64=None, regenerate=False):
    """Get a ≤15-word suggestion from the local LLM based on audio + screen context."""
    with _model_lock:
        main_model = _active_model_main
        light_model = _active_model_light

    model = main_model
    if is_battery_saver_on() and light_model:
        model = light_model
        print(f"🔋 Battery saver active — using lightweight model: {model}")
        
    if model is None:
        return "SILENT"

    # Pre-filter hallucinated transcriptions
    if not regenerate:
        hallucination_signals = [
            len(audio_text.split()) < 4,  # too short
            sum(1 for c in audio_text if c.isupper()) > len(audio_text) * 0.3,  # too many caps
        ]
        # Check for nonsense word ratio
        words = audio_text.lower().split()
        real_words = {"the","and","for","you","that","this","with","have","file",
                      "code","loop","data","read","sent","plan","check","slow",
                      "fast","error","function","meeting","project","did","nested",
                      "running","looking","working","trying","need","know","think",
                      "said","your","our","can","will","should","would","alfie",
                      "tippu","hey","send","share","open","loop","list","slow"}
        real_count = sum(1 for w in words if w in real_words)
        if len(words) > 3 and real_count == 0:
            return "SILENT"

    # File context detection
    file_context = ""
    file_name = ""
    if is_file_mention(audio_text):
        matched_file = find_recent_file(audio_text)
        if matched_file:
            file_context = read_file_context(matched_file)
            file_name = matched_file.name
            print(f"📂 File context loaded: {file_name}")
        else:
            print("📂 File mention detected but no matching file found")

    # Background contextual mapping via active windows
    open_windows = []
    try:
        if HAS_PYGETWINDOW:
            # Get visibly titled windows to hint at broad workflow (VSCode, browsers, docs, chat apps)
            for w in gw.getWindowsWithTitle(''):
                title = w.title.strip()
                # Filter out random invisible GUI handles/empty titles
                if title and len(title) > 2 and w.visible and w.width > 0:
                    open_windows.append(title)
        else:
            # Fallback for systems without pygetwindow
            # Attempt to get process names as a very basic context hint
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] and proc.info['name'].endswith('.exe'): # Basic filter for Windows executables
                    open_windows.append(proc.info['name'].replace('.exe', ''))
            # Limit to a reasonable number to avoid overwhelming the context
            open_windows = list(set(open_windows))[:10]
    except Exception as e:
        print(f"⚠️ Window/Process fetch error: {e}")
        
    window_context = ""
    if open_windows:
        # Keep it brief to save token load
        sampled_windows = list(set(open_windows))[:10] 
        window_context = "\nCurrently open background apps & tabs:\n" + "\n".join(f"- {t}" for t in sampled_windows)

    user_content = f"""Audio transcription: "{audio_text}"
{window_context}

Is this transcription clearly work-related, technical, or professional context?
If YES — give ONE specific suggestion in 15 words or fewer.
If there are multiple distinct but likely interpretations or similar data sources, provide 2-3 options separated by the '|' character.
If NO, unclear, or random — respond with SILENT only.
No exceptions. Do not explain. Just the suggestion or the word SILENT."""

    if file_context:
        user_content = f"""Audio transcription: "{audio_text}"
{window_context}

A file was mentioned and found on the device: {file_name}
File contents (first 1500 chars):
{file_context}

The user's name was called and a file was referenced in conversation.
Give a SHORT, specific response they can say out loud to answer the question about this file.
If there are multiple possible answers in the file, provide 2-3 options separated by the '|' character.
Maximum 20 words per option. Sound natural, like you read the file. No preamble."""

    # Inject active session RAM learning
    learning_prompt = SYSTEM_PROMPT
    if session_preferences["likes"] or session_preferences["dislikes"]:
        learning_prompt += "\n\nCRITICAL USER PREFERENCES FOR THIS SESSION:\n"
        if session_preferences["likes"]:
            learning_prompt += f"DO MORE OF: {', '.join(session_preferences['likes'])}\n"
        if session_preferences["dislikes"]:
            learning_prompt += f"AVOID: {', '.join(session_preferences['dislikes'])}\n"

    messages = [
        {"role": "system", "content": learning_prompt},
        {"role": "user", "content": user_content}
    ]

    temp = 0.9 if regenerate else 0.7
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"num_predict": 40, "temperature": temp}
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=12)
        response.raise_for_status()

        # Safe response parsing — never assume key structure
        data = response.json()
        suggestion = ""
        if isinstance(data, dict):
            msg = data.get("message", {})
            if isinstance(msg, dict):
                suggestion = msg.get("content", "").strip()

        if not suggestion:
            return "SILENT"

        # Word count enforcement — Mistral ignores the 15-word rule sometimes
        words = suggestion.split()
        if len(words) > 20:
            suggestion = " ".join(words[:20])

        if "SILENT" in suggestion.upper():
            return "SILENT"

        del messages, payload, data
        gc.collect()

        return suggestion

    except requests.exceptions.Timeout:
        print("⚠️  LLM timeout — skipping")
        return "SILENT"
    except Exception as e:
        print(f"⚠️  LLM error: {e}")
        return "SILENT"
