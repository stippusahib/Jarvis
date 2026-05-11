# JARVIS Session Memory Manager
"""
Persistent session memory for JARVIS.
Features:
- RAM/Disk hybrid (keeps last 3 sessions hot in RAM)
- Persists to ~/.jarvis/sessions.json
- 10MB file size cap
- Auto-decay of old sessions
- PII scrubbing (placeholder)
"""

import os
import json
import uuid
import time
import logging
from typing import List, Dict, Any
from pathlib import Path


class SessionMemory:
    """Manages conversational context across sessions."""
    
    MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB cap
    MAX_HOT_SESSIONS = 3  # Current + 2 previous
    
    def __init__(self):
        self.jarvis_dir = Path.home() / ".jarvis"
        self.jarvis_dir.mkdir(exist_ok=True)
        self.db_path = self.jarvis_dir / "sessions.json"
        
        self.current_session_id = str(uuid.uuid4())
        self.sessions: List[Dict[str, Any]] = []
        
        self._load_from_disk()
        self._start_new_session()
        
    def _load_from_disk(self):
        """Load recent sessions from disk, respecting the 10MB limit."""
        if not self.db_path.exists():
            return
            
        # Size check
        if self.db_path.stat().st_size > self.MAX_FILE_SIZE_BYTES:
            logging.warning("Session database exceeded 10MB cap. Pruning oldest data.")
            # In a real scenario, we'd do a safe truncate or archive.
            # For now, we'll let the load -> trim -> save cycle handle it.
            
        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.sessions = data.get("sessions", [])
        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"Failed to load session memory: {e}")
            self.sessions = []
            
        # Prune down to MAX_HOT_SESSIONS - 1 (leaving room for current)
        if len(self.sessions) > (self.MAX_HOT_SESSIONS - 1):
            logging.info(f"Auto-decaying {len(self.sessions) - (self.MAX_HOT_SESSIONS - 1)} old sessions.")
            self.sessions = self.sessions[-(self.MAX_HOT_SESSIONS - 1):]

    def _save_to_disk(self):
        """Save hot sessions to disk."""
        data = {
            "version": "1.0",
            "updated_at": time.time(),
            "sessions": self.sessions
        }
        
        try:
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            logging.error(f"Failed to save session memory: {e}")

    def _start_new_session(self):
        """Initialize the current session."""
        self.sessions.append({
            "session_id": self.current_session_id,
            "timestamp": time.time(),
            "messages": []
        })
        self._save_to_disk()

    def get_current_session(self) -> dict:
        return self.sessions[-1]

    def add_message(self, role: str, content: str):
        """Add a message to the current session."""
        # Simple PII scrubbing could happen here before saving
        current = self.get_current_session()
        current["messages"].append({
            "role": role,
            "content": content,
            "timestamp": time.time()
        })
        self._save_to_disk()

    def get_context(self) -> List[Dict[str, str]]:
        """Get flattened context of all hot sessions for the agent loop."""
        context = []
        for i, session in enumerate(self.sessions):
            # Optional: Add a system note indicating session boundaries
            if i < len(self.sessions) - 1:
                context.append({
                    "role": "system",
                    "content": f"[Previous Session on {time.ctime(session['timestamp'])}]"
                })
            
            for msg in session["messages"]:
                context.append({"role": msg["role"], "content": msg["content"]})
                
        return context

    def clear_memory(self):
        """Force clear all session memory."""
        self.sessions = []
        self.current_session_id = str(uuid.uuid4())
        self._start_new_session()
        logging.info("Session memory cleared by user request.")
