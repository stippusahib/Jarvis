# JARVIS Engine Module
"""
Inference engine adapters.
Standardizes LLM communication across different backends.
"""

import requests
import json
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class BaseEngine(ABC):
    """Base class for all inference engines."""
    
    name = "base"
    
    @abstractmethod
    def is_healthy(self) -> bool:
        """Check if the engine is available and responding."""
        pass
        
    @abstractmethod
    def generate(self, model: str, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        """Generate a response from the LLM."""
        pass


class OllamaEngine(BaseEngine):
    """Ollama backend engine."""
    
    name = "ollama"
    
    def __init__(self, host: str = "http://127.0.0.1:11434"):
        self.host = host.rstrip("/")
        self.api_url = f"{self.host}/api/chat"
        self.tags_url = f"{self.host}/api/tags"
        
    def is_healthy(self) -> bool:
        try:
            r = requests.get(self.tags_url, timeout=2)
            return r.status_code == 200
        except Exception:
            return False

    def generate(self, model: str, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }
        try:
            response = requests.post(self.api_url, json=payload, timeout=120)
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "")
        except requests.RequestException as e:
            logging.error(f"Ollama generation failed: {e}")
            raise RuntimeError(f"Ollama backend error: {e}")


class LMStudioEngine(BaseEngine):
    """LM Studio (OpenAI-compatible) backend engine."""
    
    name = "lmstudio"
    
    def __init__(self, host: str = "http://127.0.0.1:1234"):
        self.host = host.rstrip("/")
        self.api_url = f"{self.host}/v1/chat/completions"
        self.models_url = f"{self.host}/v1/models"
        
    def is_healthy(self) -> bool:
        try:
            r = requests.get(self.models_url, timeout=2)
            return r.status_code == 200
        except Exception:
            return False

    def generate(self, model: str, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "temperature": temperature
        }
        try:
            response = requests.post(self.api_url, json=payload, timeout=120)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except requests.RequestException as e:
            logging.error(f"LMStudio generation failed: {e}")
            raise RuntimeError(f"LMStudio backend error: {e}")

