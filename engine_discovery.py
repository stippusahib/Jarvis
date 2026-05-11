# JARVIS Engine Discovery
"""
Automatically finds and connects to the best available local LLM backend.
"""

import logging
from typing import Optional, Tuple
from engine import BaseEngine, OllamaEngine, LMStudioEngine

def discover_best_engine() -> Tuple[Optional[BaseEngine], str]:
    """
    Check configured engines and return the first healthy one,
    along with its recommended default model.
    """
    # 1. Try LM Studio first (usually running heavier models if active)
    lmstudio = LMStudioEngine()
    if lmstudio.is_healthy():
        logging.info("Discovered active LM Studio backend.")
        # LM Studio ignores the model name if it's already loaded
        return lmstudio, "local-model"
        
    # 2. Try Ollama
    ollama = OllamaEngine()
    if ollama.is_healthy():
        logging.info("Discovered active Ollama backend.")
        return ollama, "mistral"
        
    logging.error("No active inference engines discovered.")
    return None, ""
