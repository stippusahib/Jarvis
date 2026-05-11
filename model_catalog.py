# JARVIS Model Catalog — Hardware-aware model selection.
# Adapted from OpenJarvis intelligence/model_catalog.py + core/config.py
"""
Built-in model catalog with hardware-aware recommendation.

Instead of hardcoded PREFERRED_MODELS = ["mistral", "llama3.2"], this module
defines ModelSpec entries with VRAM requirements, quantization info, and
supported engines. The recommend_model() function picks the best model
that fits the user's actual hardware.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class ModelSpec:
    """Specification for a known model."""
    model_id: str                     # e.g. "mistral:7b", "llama3.2:3b"
    name: str                         # Human-readable name
    parameter_count_b: float          # Billions of parameters
    context_length: int = 8192        # Max context window
    min_vram_gb: float = 0.0          # Minimum VRAM to run comfortably
    supported_engines: Tuple[str, ...] = ("ollama",)
    provider: str = "local"           # "meta", "mistral", "alibaba", etc.
    vision: bool = False              # Supports image input
    tool_calling: bool = False        # Supports function/tool calling
    quantization: str = "q4_k_m"     # Default quantization
    metadata: Dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Built-in model catalog
# ---------------------------------------------------------------------------

BUILTIN_MODELS: List[ModelSpec] = [
    # ── Tiny (≤4GB RAM) ─────────────────────────────────
    ModelSpec(
        model_id="phi3:mini",
        name="Phi-3 Mini (3.8B)",
        parameter_count_b=3.8,
        context_length=4096,
        min_vram_gb=2.5,
        supported_engines=("ollama", "llamacpp"),
        provider="microsoft",
    ),
    ModelSpec(
        model_id="tinyllama",
        name="TinyLlama (1.1B)",
        parameter_count_b=1.1,
        context_length=2048,
        min_vram_gb=1.0,
        supported_engines=("ollama", "llamacpp"),
        provider="tinyllama",
    ),
    ModelSpec(
        model_id="qwen3:0.6b",
        name="Qwen3 0.6B",
        parameter_count_b=0.6,
        context_length=40960,
        min_vram_gb=0.5,
        supported_engines=("ollama", "llamacpp", "vllm"),
        provider="alibaba",
    ),
    ModelSpec(
        model_id="qwen3:1.7b",
        name="Qwen3 1.7B",
        parameter_count_b=1.7,
        context_length=40960,
        min_vram_gb=1.5,
        supported_engines=("ollama", "llamacpp", "vllm"),
        provider="alibaba",
    ),

    # ── Small (4-8GB RAM) ───────────────────────────────
    ModelSpec(
        model_id="llama3.2:3b",
        name="LLaMA 3.2 (3B)",
        parameter_count_b=3.0,
        context_length=8192,
        min_vram_gb=2.5,
        supported_engines=("ollama", "llamacpp", "vllm"),
        provider="meta",
        tool_calling=True,
    ),
    ModelSpec(
        model_id="qwen3:4b",
        name="Qwen3 4B",
        parameter_count_b=4.0,
        context_length=40960,
        min_vram_gb=3.0,
        supported_engines=("ollama", "llamacpp", "vllm"),
        provider="alibaba",
        tool_calling=True,
    ),
    ModelSpec(
        model_id="gemma2:2b",
        name="Gemma 2 (2B)",
        parameter_count_b=2.0,
        context_length=8192,
        min_vram_gb=2.0,
        supported_engines=("ollama", "llamacpp"),
        provider="google",
    ),

    # ── Medium (8-16GB RAM) ─────────────────────────────
    ModelSpec(
        model_id="mistral",
        name="Mistral 7B",
        parameter_count_b=7.3,
        context_length=8192,
        min_vram_gb=5.0,
        supported_engines=("ollama", "llamacpp", "vllm"),
        provider="mistral",
        tool_calling=True,
    ),
    ModelSpec(
        model_id="llama3.2",
        name="LLaMA 3.2 (8B)",
        parameter_count_b=8.0,
        context_length=8192,
        min_vram_gb=5.5,
        supported_engines=("ollama", "llamacpp", "vllm"),
        provider="meta",
        tool_calling=True,
    ),
    ModelSpec(
        model_id="qwen3:8b",
        name="Qwen3 8B",
        parameter_count_b=8.0,
        context_length=40960,
        min_vram_gb=5.5,
        supported_engines=("ollama", "llamacpp", "vllm"),
        provider="alibaba",
        tool_calling=True,
    ),
    ModelSpec(
        model_id="gemma2:9b",
        name="Gemma 2 (9B)",
        parameter_count_b=9.2,
        context_length=8192,
        min_vram_gb=6.0,
        supported_engines=("ollama", "llamacpp"),
        provider="google",
    ),

    # ── Large (16-32GB RAM) ─────────────────────────────
    ModelSpec(
        model_id="mistral-nemo",
        name="Mistral Nemo (12B)",
        parameter_count_b=12.0,
        context_length=16384,
        min_vram_gb=8.0,
        supported_engines=("ollama", "llamacpp", "vllm"),
        provider="mistral",
        tool_calling=True,
    ),
    ModelSpec(
        model_id="qwen3:14b",
        name="Qwen3 14B",
        parameter_count_b=14.0,
        context_length=40960,
        min_vram_gb=10.0,
        supported_engines=("ollama", "llamacpp", "vllm"),
        provider="alibaba",
        tool_calling=True,
    ),
    ModelSpec(
        model_id="deepseek-coder-v2:16b",
        name="DeepSeek Coder V2 (16B)",
        parameter_count_b=16.0,
        context_length=16384,
        min_vram_gb=10.0,
        supported_engines=("ollama", "llamacpp", "vllm"),
        provider="deepseek",
        tool_calling=True,
    ),

    # ── XL (32GB+ RAM) ─────────────────────────────────
    ModelSpec(
        model_id="qwen3:32b",
        name="Qwen3 32B",
        parameter_count_b=32.0,
        context_length=40960,
        min_vram_gb=20.0,
        supported_engines=("ollama", "llamacpp", "vllm"),
        provider="alibaba",
        tool_calling=True,
    ),
    ModelSpec(
        model_id="llama3.1:70b",
        name="LLaMA 3.1 (70B)",
        parameter_count_b=70.0,
        context_length=8192,
        min_vram_gb=40.0,
        supported_engines=("ollama", "vllm"),
        provider="meta",
        tool_calling=True,
    ),

    # ── Vision Models ───────────────────────────────────
    ModelSpec(
        model_id="llava",
        name="LLaVA 1.6 (7B)",
        parameter_count_b=7.0,
        context_length=4096,
        min_vram_gb=5.0,
        supported_engines=("ollama",),
        provider="llava",
        vision=True,
    ),
    ModelSpec(
        model_id="llava:13b",
        name="LLaVA 1.6 (13B)",
        parameter_count_b=13.0,
        context_length=4096,
        min_vram_gb=9.0,
        supported_engines=("ollama",),
        provider="llava",
        vision=True,
    ),
    ModelSpec(
        model_id="llava-llama3",
        name="LLaVA LLaMA3 (8B)",
        parameter_count_b=8.0,
        context_length=4096,
        min_vram_gb=5.5,
        supported_engines=("ollama",),
        provider="llava",
        vision=True,
    ),
    ModelSpec(
        model_id="moondream",
        name="Moondream (1.8B)",
        parameter_count_b=1.8,
        context_length=2048,
        min_vram_gb=1.5,
        supported_engines=("ollama",),
        provider="vikhyat",
        vision=True,
    ),
]

# Build lookup dict for fast access
_CATALOG: Dict[str, ModelSpec] = {spec.model_id: spec for spec in BUILTIN_MODELS}


# ---------------------------------------------------------------------------
# Memory tier table — maps available memory → max model size
# Adapted from OpenJarvis config.py:255-260
# ---------------------------------------------------------------------------

_MODEL_TIERS = [
    # (max_available_gb, preferred_model_id, fallback_model_id)
    (4,  "qwen3:1.7b",    "tinyllama"),
    (8,  "llama3.2:3b",   "phi3:mini"),
    (12, "mistral",       "qwen3:8b"),
    (16, "qwen3:8b",      "mistral"),
    (24, "qwen3:14b",     "mistral-nemo"),
    (32, "qwen3:14b",     "deepseek-coder-v2:16b"),
    (48, "qwen3:32b",     "qwen3:14b"),
]

_VISION_TIERS = [
    # (max_available_gb, vision_model_id)
    (4,  "moondream"),
    (8,  "llava"),
    (12, "llava"),
    (24, "llava:13b"),
]


def _available_memory_gb(gpu_vram_gb: float, ram_gb: float) -> float:
    """Return usable memory in GB for model loading.

    If GPU VRAM is available, use 90% of it.
    Otherwise, use RAM minus 4GB for OS overhead, then 80%.
    """
    if gpu_vram_gb > 0:
        return gpu_vram_gb * 0.9
    if ram_gb > 0:
        return (ram_gb - 4) * 0.8
    return 0.0


def recommend_model(
    gpu_vram_gb: float = 0.0,
    ram_gb: float = 0.0,
    available_models: Optional[List[str]] = None,
    engine: str = "ollama",
) -> Optional[ModelSpec]:
    """Pick the best model that fits the user's hardware.

    Args:
        gpu_vram_gb: Detected GPU VRAM in GB
        ram_gb: Total system RAM in GB
        available_models: List of model IDs currently installed (from Ollama /api/tags)
        engine: The active inference engine

    Returns:
        Best matching ModelSpec, or None if nothing fits
    """
    available_gb = _available_memory_gb(gpu_vram_gb, ram_gb)
    if available_gb <= 0:
        return None

    # If we know what's installed, prefer the best installed model
    if available_models:
        # Score each installed model by parameter count (bigger = better, if it fits)
        best = None
        best_params = 0.0
        for model_id in available_models:
            # Handle Ollama's naming: "mistral:latest" → "mistral"
            base_id = model_id.split(":latest")[0] if model_id.endswith(":latest") else model_id
            spec = _CATALOG.get(base_id) or _CATALOG.get(model_id)
            if spec is None:
                continue
            if spec.min_vram_gb > available_gb:
                continue  # Too big for hardware
            if engine not in spec.supported_engines:
                continue
            if spec.vision:
                continue  # Vision models handled separately
            if spec.parameter_count_b > best_params:
                best = spec
                best_params = spec.parameter_count_b
        if best:
            return best

    # Fallback: use tier table
    for max_gb, preferred_id, fallback_id in _MODEL_TIERS:
        if available_gb <= max_gb:
            spec = _CATALOG.get(preferred_id)
            if spec and engine in spec.supported_engines:
                return spec
            spec = _CATALOG.get(fallback_id)
            if spec and engine in spec.supported_engines:
                return spec
            break

    # Last resort: largest model that fits
    candidates = [
        s for s in BUILTIN_MODELS
        if not s.vision
        and s.min_vram_gb <= available_gb
        and engine in s.supported_engines
    ]
    candidates.sort(key=lambda s: s.parameter_count_b, reverse=True)
    return candidates[0] if candidates else None


def recommend_vision_model(
    gpu_vram_gb: float = 0.0,
    ram_gb: float = 0.0,
    available_models: Optional[List[str]] = None,
) -> Optional[ModelSpec]:
    """Pick the best vision model that fits the hardware."""
    available_gb = _available_memory_gb(gpu_vram_gb, ram_gb)
    if available_gb <= 0:
        return None

    # Check what's installed first
    if available_models:
        best = None
        best_params = 0.0
        for model_id in available_models:
            base_id = model_id.split(":latest")[0] if model_id.endswith(":latest") else model_id
            spec = _CATALOG.get(base_id) or _CATALOG.get(model_id)
            if spec and spec.vision and spec.min_vram_gb <= available_gb:
                if spec.parameter_count_b > best_params:
                    best = spec
                    best_params = spec.parameter_count_b
        if best:
            return best

    # Tier table
    for max_gb, vision_id in _VISION_TIERS:
        if available_gb <= max_gb:
            return _CATALOG.get(vision_id)

    return _CATALOG.get("llava")


def recommend_lightweight_model(
    gpu_vram_gb: float = 0.0,
    ram_gb: float = 0.0,
) -> Optional[ModelSpec]:
    """Pick the smallest usable model for low-latency tasks (permission checks, etc.)."""
    available_gb = _available_memory_gb(gpu_vram_gb, ram_gb)
    candidates = [
        s for s in BUILTIN_MODELS
        if not s.vision and s.min_vram_gb <= available_gb
    ]
    candidates.sort(key=lambda s: s.parameter_count_b)
    return candidates[0] if candidates else None


def get_model_spec(model_id: str) -> Optional[ModelSpec]:
    """Look up a model by ID."""
    return _CATALOG.get(model_id)


def list_models_for_vram(available_gb: float) -> List[ModelSpec]:
    """Return all models that fit within the given VRAM budget."""
    return [s for s in BUILTIN_MODELS if s.min_vram_gb <= available_gb]


__all__ = [
    "ModelSpec",
    "BUILTIN_MODELS",
    "recommend_model",
    "recommend_vision_model",
    "recommend_lightweight_model",
    "get_model_spec",
    "list_models_for_vram",
]
