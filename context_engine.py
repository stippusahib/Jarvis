# PRIVACY: RAM-only. Zero disk I/O.
import requests
import gc
import time
import threading

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
OLLAMA_TAGS_URL = "http://127.0.0.1:11434/api/tags"
PREFERRED_MODELS = ["mistral", "phi3:mini", "llama3.2"]
_active_model = None
_model_lock = threading.Lock()  # REQUIRED — prevents race condition on _active_model

SYSTEM_PROMPT = """You are Second Brain — a silent ambient AI assistant running fully offline on the user's device.
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


def detect_available_model():
    """Query Ollama for available models and pick the best one."""
    try:
        response = requests.get(OLLAMA_TAGS_URL, timeout=5)
        response.raise_for_status()
        data = response.json()
        available = data.get("models", [])
        for preferred in PREFERRED_MODELS:
            for model in available:
                model_name = model.get("name", "")
                if preferred in model_name:
                    return model_name  # Return full name like "mistral:latest"
    except Exception:
        pass
    return None


def prewarm_ollama():
    """Pre-warm Ollama at startup so first real suggestion is fast."""
    global _active_model
    model = detect_available_model()
    with _model_lock:
        _active_model = model

    if _active_model:
        try:
            requests.post(OLLAMA_URL, json={
                "model": _active_model,
                "messages": [{"role": "user", "content": "hi"}],
                "stream": False,
                "options": {"num_predict": 1}
            }, timeout=15)
            print(f"✅ Ollama ready — using: {_active_model}")
        except Exception:
            print("⚠️  Ollama pre-warm failed — first suggestion may be slow")
    else:
        print("⚠️  Ollama not reachable. Run: ollama serve")


def get_suggestion(audio_text, screen_b64=None):
    """Get a ≤15-word suggestion from the local LLM based on audio + screen context."""
    with _model_lock:
        model = _active_model

    if model is None:
        return "SILENT"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"What I just heard: {audio_text}\nScreen context: {'available' if screen_b64 else 'none'}"}
    ]

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"num_predict": 40, "temperature": 0.7}
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
