# JARVIS Loop Guard — Prevents degenerate agent loops
"""
Detect and prevent degenerate agent tool-calling loops.
Adapted from OpenJarvis agents/loop_guard.py (Python fallback).

Features:
1. Hash tracking: blocks identical calls after max_identical_calls
2. Per-tool budget: blocks a single tool from being used too many times per session
3. Ping-pong detection: stops A-B-A-B repeating tool patterns
"""

import hashlib
import json
from collections import deque
from dataclasses import dataclass
from typing import Dict


@dataclass
class LoopGuardConfig:
    """Configuration for the loop guard."""
    enabled: bool = True
    max_identical_calls: int = 3
    poll_tool_budget: int = 5
    ping_pong_window: int = 6


@dataclass
class LoopVerdict:
    """Result of a loop guard check."""
    blocked: bool = False
    reason: str = ""
    warned: bool = False


class LoopGuard:
    """Detect and prevent degenerate agent loops."""

    def __init__(self, config: LoopGuardConfig = None):
        self._config = config or LoopGuardConfig()
        # Track call hashes and their counts
        self._call_counts: Dict[str, int] = {}
        # Track tool name sequence for pattern detection
        self._tool_sequence: deque = deque(maxlen=self._config.ping_pong_window)
        # Track per-tool call counts
        self._per_tool_counts: Dict[str, int] = {}

    def check_call(self, tool_name: str, arguments: dict) -> LoopVerdict:
        """Check whether a tool call should proceed or be blocked."""
        if not self._config.enabled:
            return LoopVerdict()

        # Serialize args for hashing (sort keys for consistency)
        try:
            arg_str = json.dumps(arguments, sort_keys=True)
        except Exception:
            arg_str = str(arguments)

        # 1. Hash tracking — identical calls
        call_hash = hashlib.sha256(f"{tool_name}:{arg_str}".encode()).hexdigest()[:16]
        self._call_counts[call_hash] = self._call_counts.get(call_hash, 0) + 1
        
        if self._call_counts[call_hash] > self._config.max_identical_calls:
            return LoopVerdict(
                blocked=True,
                reason=(
                    f"Blocked by LoopGuard: Identical call to '{tool_name}' "
                    f"repeated {self._call_counts[call_hash]} times. "
                    "Try a different approach or give a Final Answer."
                ),
            )

        # 2. Per-tool budget
        self._per_tool_counts[tool_name] = self._per_tool_counts.get(tool_name, 0) + 1
        if self._per_tool_counts[tool_name] > self._config.poll_tool_budget:
            return LoopVerdict(
                blocked=True,
                reason=(
                    f"Blocked by LoopGuard: Tool '{tool_name}' exceeded max "
                    f"usage budget ({self._config.poll_tool_budget} times). "
                    "You must give a Final Answer."
                ),
            )

        # 3. Ping-pong detection (A-B-A-B pattern)
        self._tool_sequence.append(tool_name)
        if len(self._tool_sequence) == self._config.ping_pong_window:
            if self._detect_ping_pong():
                return LoopVerdict(
                    blocked=True,
                    reason="Blocked by LoopGuard: Repetitive ping-pong tool pattern detected. Stop and give a Final Answer.",
                )

        return LoopVerdict()

    def _detect_ping_pong(self) -> bool:
        """Detect A-B-A-B or A-B-C-A-B-C patterns in the tool sequence."""
        seq = list(self._tool_sequence)
        n = len(seq)
        
        # Check for A-B-A-B (period 2)
        if n >= 4:
            if seq[-1] == seq[-3] and seq[-2] == seq[-4]:
                return True
                
        # Check for A-B-C-A-B-C (period 3)
        if n >= 6:
            if seq[-1] == seq[-4] and seq[-2] == seq[-5] and seq[-3] == seq[-6]:
                return True
                
        return False

    def compress_context(self, messages: list) -> list:
        """
        Prevent context window overflow by compressing the message history.
        Only keeps system prompt and last N messages.
        """
        MAX_MESSAGES = 15
        if len(messages) <= MAX_MESSAGES:
            return messages
            
        # Keep system prompt (index 0) and the most recent messages
        system_prompt = [m for m in messages if m.get("role") == "system"]
        if system_prompt:
            return [system_prompt[0]] + messages[-(MAX_MESSAGES-1):]
        else:
            return messages[-MAX_MESSAGES:]

    def reset(self):
        """Reset the loop guard state for a new request."""
        self._call_counts.clear()
        self._tool_sequence.clear()
        self._per_tool_counts.clear()

