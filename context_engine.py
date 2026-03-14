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
OLLAMA_VISION_URL = "http://127.0.0.1:11434/api/chat"
PREFERRED_MODELS = ["qwen2.5", "mistral", "llama3.2"]
LIGHTWEIGHT_MODELS = ["phi3:mini", "tinyllama"]
LLAVA_MODELS = ["llava", "llava:latest", "llava:7b"]
_active_model_main = None
_active_model_light = None
_vision_model = None
_model_lock = threading.Lock()

VISION_TRIGGER_KEYWORDS = [
    # Coding / debugging
    "error", "bug", "bugs", "loop", "function", "slow", "crash", "fix",
    "not working", "why", "issue", "problem", "code", "variable",
    "exception", "debug", "performance", "optimize", "broken",
    "help me fix", "fix this", "whats wrong", "what's wrong",
    "why is this", "this isn't", "doesn't work", "not compiling",
    "traceback", "syntax", "undefined", "null", "none", "failed",
    "help", "stuck", "wrong", "incorrect", "mistake",
    # Document / research / diagrams
    "diagram", "chart", "image", "graph", "table", "figure",
    "what does", "what is", "explain", "describe", "drawing",
    "flowchart", "architecture", "design",
    # Screen reference
    "screen", "showing", "visible", "see this", "look at",
    "on screen", "right here", "this code", "this file",
    "this function", "this error", "this line", "here"
]

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
            res = ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status))  # type: ignore
            if res:
                # SystemStatusFlag bit 0 is battery saver
                return bool(status.SystemStatusFlag & 1)  # type: ignore
    except Exception as e:
        print(f"Power check failed: {e}")
    return False

SYSTEM_PROMPT = """You are JARVIS — a fully offline AI assistant on the user's device.
You perceive their screen and hear what they say in real-time.

Your job: give ONE hyper-specific, immediately useful response in 15 words or fewer.

Context detection — adapt your response style:
- If user is CODING: suggest performance fixes, bugs, or patterns
- If user is in a MEETING: suggest social cues, names, action items
- If user is WRITING: suggest clarity, missing points, or next steps
- If user asks a DIRECT QUESTION: answer it directly
- If user is BROWSING: suggest related concepts worth knowing now

Rules:
- Never ask questions
- Never give generic advice
- If the user asks something directly, always respond — never say SILENT
- If nothing useful and no direct question: respond with exactly SILENT
- 15 words maximum. Sound like a genius friend, not a chatbot.
- Be specific and direct

Good examples:
"That nested loop is O(n²) — a dict lookup cuts it to O(1)."
"John just said your name — unmute now."
"Yes — the plan covers offline AI, Ghost HUD, and zero storage."
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


def detect_vision_model() -> str | None:
    """Check if LLaVA vision model is available in Ollama."""
    try:
        response = requests.get(OLLAMA_TAGS_URL, timeout=5)
        response.raise_for_status()
        data = response.json()
        available = data.get("models", [])
        for model in available:
            model_name = model.get("name", "")
            for lm in LLAVA_MODELS:
                if lm.split(":")[0] in model_name:
                    return model_name
    except Exception:
        pass
    return None


def _compress_for_vision(screen_b64: str) -> str:
    """Resize image to 800x450 for faster LLaVA processing without losing readability."""
    try:
        import base64 as b64lib
        import io as _io
        from PIL import Image as _Image
        img_bytes = b64lib.b64decode(screen_b64)
        img = _Image.open(_io.BytesIO(img_bytes))
        img.thumbnail((800, 450), _Image.LANCZOS)
        buf = _io.BytesIO()
        img.save(buf, format="JPEG", quality=50)
        return b64lib.b64encode(buf.getvalue()).decode("utf-8")
    except Exception:
        return screen_b64  # fallback to original if compression fails


def get_screen_description(screen_b64: str) -> str:
    """Use LLaVA to describe what is visible on screen.
    Detects code, errors, diagrams, documents.
    Returns text description or empty string.
    Never crashes.
    """
    global _vision_model

    if _vision_model is None:
        _vision_model = detect_vision_model()

    if not _vision_model or not screen_b64:
        return ""

    try:
        payload = {
            "model": _vision_model,
            "messages": [{
                "role": "user",
                "content": (
                    "In 2 sentences max describe: "
                    "1) What app is open "
                    "2) Any visible code, errors, or key text. "
                    "Be specific — mention function names, variable names, or error messages if visible. "
                    "No generic descriptions."
                ),
                "images": [_compress_for_vision(screen_b64)]
            }],
            "stream": False,
            "options": {"num_predict": 200, "temperature": 0.2}
        }

        response = requests.post(OLLAMA_VISION_URL, json=payload, timeout=20)
        response.raise_for_status()

        data = response.json()
        description = ""
        if isinstance(data, dict):
            msg = data.get("message", {})
            if isinstance(msg, dict):
                description = msg.get("content", "").strip()

        if description:
            print(f"👁️  Screen: {description[:100]}...")

        del payload, data
        gc.collect()
        return description

    except requests.exceptions.Timeout:
        print("⚠️  Vision timeout — skipping screen context")
        return ""
    except Exception as e:
        print(f"⚠️  Vision error: {e}")
        return ""


def smart_truncate(text: str, max_words: int = 20) -> str:
    """Truncate text at natural sentence boundary.
    Never cuts mid-sentence if a full stop exists within range.
    """
    words = text.split()
    if len(words) <= max_words:
        return text

    sentence_enders = ['.', '!', '?']

    # Search for natural end within first 28 words
    best_cut = -1
    for i, word in enumerate(words[:28]):
        if any(word.endswith(ender) for ender in sentence_enders):
            best_cut = i

    if best_cut > 4:
        # Good sentence end found
        return " ".join(words[:best_cut + 1])
    else:
        # No sentence end — hard cut but add ellipsis
        return " ".join(words[:max_words])


def prewarm_ollama():
    """Pre-warm Ollama at startup so first real suggestion is fast."""
    global _active_model_main, _active_model_light, _vision_model
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

    # Detect vision model
    _vision_model = detect_vision_model()
    if _vision_model:
        print(f"👁️  Vision model ready: {_vision_model}")
    else:
        print("⚠️  No vision model — run: ollama pull llava")


def get_suggestion(audio_text, screen_b64=None, regenerate=False, force_vision=False):
    """Get a suggestion using audio + smart screen vision + file context.
    
    force_vision=True: always scan screen regardless of keywords (hotkey trigger)
    regenerate=True: use higher temperature for alternative suggestion
    """
    with _model_lock:
        main_model = _active_model_main
        light_model = _active_model_light

    model = main_model
    if is_battery_saver_on() and light_model:
        model = light_model
        print(f"🔋 Battery saver — using: {model}")

    if model is None:
        return "SILENT"

    # Pre-filter hallucinated transcriptions
    if not regenerate and not force_vision:
        words = audio_text.lower().split()
        real_words = {
            "the","and","for","you","that","this","with","have","file",
            "code","loop","data","read","sent","plan","check","slow",
            "fast","error","bug","function","meeting","project","did",
            "nested","running","looking","working","trying","need","know",
            "think","said","your","our","can","will","should","would",
            "alfie","tippu","hey","send","share","open","list","fix",
            "help","why","what","screen","see","showing","crash","issue",
            "problem","broken","works","debug","variable","syntax","null"
        }
        real_count = sum(1 for w in words if w in real_words)
        if len(words) > 3 and real_count == 0:
            return "SILENT"

    # Quick answers for common questions JARVIS can handle offline
    audio_lower_quick = audio_text.lower()

    if any(w in audio_lower_quick for w in ["what time", "what's the time", "current time", "time now", "time is it"]):
        from datetime import datetime
        now = datetime.now()
        return f"It's {now.strftime('%I:%M %p')} — {now.strftime('%A')}."

    if any(w in audio_lower_quick for w in ["what date", "today's date", "what day", "current date"]):
        from datetime import datetime
        now = datetime.now()
        return f"Today is {now.strftime('%A, %B %d %Y')}."

    if any(w in audio_lower_quick for w in ["what's the weather", "weather today", "is it raining"]):
        return "I'm fully offline — check a weather app for current conditions."

    if any(w in audio_lower_quick for w in ["who are you", "what are you", "introduce yourself"]):
        return "JARVIS — offline ambient AI. I see your screen, hear you, store nothing."

    if any(w in audio_lower_quick for w in ["how are you", "you okay", "you good"]):
        return "Running clean — zero disk writes, full attention on you."

    # Smart vision trigger — skip if file context will handle it
    audio_lower = audio_text.lower()
    has_file_trigger = is_file_mention(audio_text)
    should_scan = not has_file_trigger and (force_vision or any(kw in audio_lower for kw in VISION_TRIGGER_KEYWORDS))

    screen_description = ""
    if screen_b64 and should_scan:
        if force_vision:
            print("🔑 Hotkey — force scanning screen...")
        else:
            print("👁️  Smart trigger — scanning screen...")
        screen_description = get_screen_description(screen_b64)
    elif screen_b64:
        print("👁️  Screen available — no trigger keywords, skipping")

    # File context detection
    file_context = ""
    file_name = ""
    if is_file_mention(audio_text):
        matched_file = find_recent_file(audio_text)
        if matched_file:
            try:
                file_context = read_file_context(matched_file)
                file_name = matched_file.name
                print(f"📂 File context loaded: {file_name}")
            except Exception as e:
                print(f"⚠️  File read error: {e}")
                file_context = ""
                file_name = ""
        else:
            print("📂 File mention detected — no matching file found")

    # Window context
    open_windows = []
    try:
        if HAS_PYGETWINDOW:
            for w in gw.getWindowsWithTitle(''):
                title = w.title.strip()
                if title and len(title) > 2 and w.visible and w.width > 0:
                    open_windows.append(title)
        else:
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] and proc.info['name'].endswith('.exe'):
                    open_windows.append(proc.info['name'].replace('.exe', ''))
            open_windows = list(set(open_windows))[:10]
    except Exception:
        pass

    window_context = ""
    if open_windows:
        sampled = list(set(open_windows))[:8]
        window_context = "\nOpen apps: " + ", ".join(sampled)

    screen_context_line = ""
    if screen_description:
        screen_context_line = f"\nScreen content: {screen_description}"

    # Detect if screen shows code (for hotkey code response)
    is_code_context = force_vision and screen_description and any(
        kw in screen_description.lower() for kw in
        ["code", "function", "error", "variable", "def ", "class ", "import", "return", "loop", "syntax"]
    )

    # Build user content
    if file_context:
        user_content = f"""Someone asked about a file. You have read it. Answer as if you read it personally.

File name: {file_name}
File contents:
{file_context}
{screen_context_line}

Question from audio: "{audio_text}"

RULES:
- Direct spoken answer in 15 words or fewer
- Reference SPECIFIC content from the file
- Sound natural — like you read it yourself
- NEVER say "open the file" or "check the file"
- NEVER ask questions
- No preamble

Good: "Yes — it covers offline AI, Ghost HUD, zero storage, and Mistral 7B."
Bad: "You should open the file to check its contents."

Answer only:"""

    elif is_code_context:
        user_content = f"""You can see code on screen. The user needs help with it.

Screen content: {screen_description}
{window_context}

User said: "{audio_text}"

Provide:
1. A brief diagnosis (what the issue is) in 1 sentence
2. The fix as a code snippet if applicable

Format your response as:
ISSUE: [one sentence diagnosis]
FIX: [corrected code or suggestion]

Be specific to the actual code visible. Maximum 40 words total."""

    else:
        user_content = f"""Audio: "{audio_text}"
{window_context}{screen_context_line}

Work-related, technical, or professional context?
If YES — ONE specific suggestion in 15 words or fewer.
If screen shows code/errors — reference it directly.
If diagram/image visible — describe what it shows briefly.
If NO or unclear — respond SILENT only.
No explanations. Just the suggestion or SILENT."""

    # Session learning
    learning_prompt = SYSTEM_PROMPT
    if session_preferences["likes"] or session_preferences["dislikes"]:
        learning_prompt += "\n\nSESSION PREFERENCES:\n"
        if session_preferences["likes"]:
            learning_prompt += f"DO MORE OF: {', '.join(session_preferences['likes'])}\n"
        if session_preferences["dislikes"]:
            learning_prompt += f"AVOID: {', '.join(session_preferences['dislikes'])}\n"

    messages = [
        {"role": "system", "content": learning_prompt},
        {"role": "user", "content": user_content}
    ]

    token_limit = 80 if is_code_context else 50
    temp = 0.9 if regenerate else 0.7

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"num_predict": token_limit, "temperature": temp}
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=15)
        response.raise_for_status()

        data = response.json()
        suggestion = ""
        if isinstance(data, dict):
            msg = data.get("message", {})
            if isinstance(msg, dict):
                suggestion = msg.get("content", "").strip()

        if not suggestion:
            return "SILENT"

        # Smart sentence completion truncation
        if not is_code_context:
            suggestion = smart_truncate(suggestion, max_words=20)

        if "SILENT" in suggestion.upper() and not is_code_context:
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
