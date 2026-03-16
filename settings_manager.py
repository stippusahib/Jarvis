# PRIVACY NOTE: This is the ONLY file that writes to disk.
# It stores user personalization settings in settings.json (same directory).
import json
import os
import pathlib

_SETTINGS_FILE = pathlib.Path(__file__).parent / "settings.json"

_DEFAULTS = {
    "user_name": "",
    "wake_words": ["jarvis", "hey jarvis", "ok jarvis", "yo jarvis"],
    "custom_paths": [],          # extra folders/files for file_scout
    "vision_keywords": [],       # extra vision trigger keywords
}

_cache: dict | None = None


def load_settings() -> dict:
    """Load settings from disk. Returns defaults if file doesn't exist."""
    global _cache
    if _cache is not None:
        return _cache

    if _SETTINGS_FILE.exists():
        try:
            with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Merge with defaults so new keys are always present
            merged = {**_DEFAULTS, **data}
            _cache = merged
            return merged
        except Exception:
            pass

    _cache = dict(_DEFAULTS)
    return _cache


def save_settings(settings: dict) -> None:
    """Save settings to disk and update cache."""
    global _cache
    _cache = settings
    try:
        with open(_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️  Failed to save settings: {e}")


def get(key: str, default=None):
    """Convenience getter."""
    return load_settings().get(key, default)


def set_key(key: str, value) -> None:
    """Update a single key and persist."""
    settings = load_settings()
    settings[key] = value
    save_settings(settings)


def reset() -> None:
    """Reset to defaults."""
    global _cache
    _cache = None
    save_settings(dict(_DEFAULTS))
