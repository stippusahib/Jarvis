# JARVIS Plugin Registry — Decorator-based hot-swap for engines, tools, agents.
# Adapted from OpenJarvis core/registry.py — simplified for our local-first stack.
"""
Decorator-based registry for runtime discovery of pluggable components.

Each typed subclass (EngineRegistry, ToolRegistry, etc.) gets its own
isolated storage so registrations never leak between registries.

Usage:
    @EngineRegistry.register("ollama")
    class OllamaEngine(BaseEngine):
        ...

    engine_cls = EngineRegistry.get("ollama")
    engine = EngineRegistry.create("ollama", host="http://127.0.0.1:11434")
"""

from __future__ import annotations
from typing import Any, Callable, Dict, Generic, Tuple, Type, TypeVar

T = TypeVar("T")


class RegistryBase(Generic[T]):
    """Generic registry base class with per-subclass isolated storage.

    Every subclass gets its own dict of entries, keyed by a string identifier.
    This means EngineRegistry and ToolRegistry never share entries even though
    they inherit from the same base.
    """

    @classmethod
    def _entries(cls) -> Dict[str, T]:
        """Get or create the entry dict for this specific registry subclass."""
        attr_name = f"_registry_entries_{cls.__name__}"
        storage = getattr(cls, attr_name, None)
        if storage is None:
            storage: Dict[str, T] = {}
            setattr(cls, attr_name, storage)
        return storage

    @classmethod
    def register(cls, key: str) -> Callable[[T], T]:
        """Decorator that registers a class/value under the given key.

        Example:
            @EngineRegistry.register("ollama")
            class OllamaEngine:
                ...
        """
        def decorator(entry: T) -> T:
            entries = cls._entries()
            if key in entries:
                # Allow re-registration (hot-reload friendly)
                pass
            entries[key] = entry
            return entry
        return decorator

    @classmethod
    def register_value(cls, key: str, value: T) -> T:
        """Imperatively register a value under a key (no decorator)."""
        cls._entries()[key] = value
        return value

    @classmethod
    def get(cls, key: str) -> T:
        """Retrieve the entry for a key. Raises KeyError if missing."""
        try:
            return cls._entries()[key]
        except KeyError:
            available = ", ".join(cls._entries().keys()) or "(none)"
            raise KeyError(
                f"{cls.__name__} has no entry for '{key}'. "
                f"Available: {available}"
            )

    @classmethod
    def create(cls, key: str, *args: Any, **kwargs: Any) -> Any:
        """Look up a key and instantiate it with the given arguments."""
        entry = cls.get(key)
        if not callable(entry):
            raise TypeError(
                f"{cls.__name__} entry '{key}' is not callable"
            )
        return entry(*args, **kwargs)

    @classmethod
    def keys(cls) -> Tuple[str, ...]:
        """Return all registered keys."""
        return tuple(cls._entries().keys())

    @classmethod
    def items(cls) -> Tuple[Tuple[str, T], ...]:
        """Return all (key, entry) pairs."""
        return tuple(cls._entries().items())

    @classmethod
    def contains(cls, key: str) -> bool:
        """Check whether a key is registered."""
        return key in cls._entries()

    @classmethod
    def clear(cls) -> None:
        """Remove all entries (useful for testing)."""
        cls._entries().clear()

    @classmethod
    def count(cls) -> int:
        """Number of registered entries."""
        return len(cls._entries())


# ---------------------------------------------------------------------------
# Typed subclass registries — one per JARVIS primitive
# ---------------------------------------------------------------------------

class EngineRegistry(RegistryBase[Type]):
    """Registry for inference engine backends (Ollama, llama.cpp, LM Studio, etc.)."""


class ToolRegistry(RegistryBase[Type]):
    """Registry for tool plugins (app control, volume, file ops, etc.)."""


class AgentRegistry(RegistryBase[Type]):
    """Registry for agent implementations (ReAct, Orchestrator, etc.)."""


class SpeechRegistry(RegistryBase[Type]):
    """Registry for speech-to-text backends (faster-whisper, etc.)."""


class TTSRegistry(RegistryBase[Type]):
    """Registry for text-to-speech backends (edge-tts, pyttsx3, etc.)."""


__all__ = [
    "RegistryBase",
    "EngineRegistry",
    "ToolRegistry",
    "AgentRegistry",
    "SpeechRegistry",
    "TTSRegistry",
]
