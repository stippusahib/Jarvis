# JARVIS Permission Manager — Safety layer for OS commands.
# Tiered permission system with voice + visual confirmation.
import threading
import time
import queue


# ─── Permission Tiers ────────────────────────────────────────────────
# AUTO:    Execute immediately, no confirmation needed
# CONFIRM: Ask user via voice + overlay popup (yes/no)
# ADMIN:   Show overlay dialog with countdown timer, must click to confirm

TIER_AUTO = "auto"
TIER_CONFIRM = "confirm"
TIER_ADMIN = "admin"

# ─── Audit Log (RAM only — wiped on exit) ─────────────────────────
_audit_log = []
_audit_lock = threading.Lock()


def log_action(intent: str, params: dict, result: str, tier: str):
    """Record an executed or denied action in RAM-only audit log."""
    with _audit_lock:
        _audit_log.append({
            "time": time.strftime("%H:%M:%S"),
            "intent": intent,
            "params": params,
            "result": result,
            "tier": tier,
        })
        # Keep last 50 entries
        if len(_audit_log) > 50:
            _audit_log.pop(0)


def get_audit_log() -> list:
    """Return audit log (RAM only)."""
    with _audit_lock:
        return list(_audit_log)


def clear_audit_log():
    """Clear audit log."""
    with _audit_lock:
        _audit_log.clear()


class PermissionManager:
    """Manages permission checks and confirmation flows for OS commands.
    
    Tiers:
    - AUTO (🟢): Safe actions — execute immediately
    - CONFIRM (🟡): Moderate — voice confirm + overlay button
    - ADMIN (🔴): Dangerous — overlay dialog with countdown
    """

    def __init__(self, voice_engine=None, overlay=None):
        self._voice = voice_engine
        self._overlay = overlay
        self._pending = queue.Queue()
        self._auto_execute_safe = True
        self._override_tier = None  # Force all to a specific tier

        # Load settings
        try:
            import settings_manager
            self._auto_execute_safe = settings_manager.get('auto_execute_safe', True)
        except Exception:
            pass

    def set_voice_engine(self, voice):
        self._voice = voice

    def set_overlay(self, overlay):
        self._overlay = overlay

    def check_permission(self, intent: str, tier: str, description: str,
                          on_approved: callable, on_denied: callable = None):
        """Check if a command has permission to execute.
        
        Args:
            intent:      Command intent name
            tier:        Permission tier (auto/confirm/admin)
            description: Human-readable description for UI
            on_approved: Called when permission is granted
            on_denied:   Called when permission is denied
        """
        effective_tier = self._override_tier or tier

        if effective_tier == TIER_AUTO and self._auto_execute_safe:
            # Auto-execute — no confirmation needed
            log_action(intent, {}, "auto_approved", effective_tier)
            on_approved()
            return

        if effective_tier == TIER_CONFIRM:
            # Voice confirmation
            self._voice_confirm(intent, description, on_approved, on_denied)
            return

        if effective_tier == TIER_ADMIN:
            # Visual dialog with countdown
            self._admin_confirm(intent, description, on_approved, on_denied)
            return

        # Unknown tier — treat as confirm
        self._voice_confirm(intent, description, on_approved, on_denied)

    def _voice_confirm(self, intent: str, description: str,
                       on_approved: callable, on_denied: callable = None):
        """Ask for voice confirmation via TTS + overlay popup."""
        if self._voice:
            self._voice.speak(f"Should I {description.lower()}?")

        if self._overlay:
            # Show confirmation popup with YES/NO
            confirm_text = f"🟡 PERMISSION: {description}\n\n[Say 'yes' or click to confirm]"
            self._overlay.show_permission_popup(
                text=confirm_text,
                on_approve=lambda: self._on_approved(intent, description, on_approved),
                on_deny=lambda: self._on_denied(intent, description, on_denied),
                timeout_ms=15000
            )
        else:
            # No overlay — auto-approve (fallback)
            log_action(intent, {}, "auto_approved_no_overlay", "confirm")
            on_approved()

    def _admin_confirm(self, intent: str, description: str,
                       on_approved: callable, on_denied: callable = None):
        """Show admin confirmation dialog with countdown timer."""
        if self._voice:
            self._voice.speak(f"Warning. {description}. Please confirm on screen.")

        if self._overlay:
            confirm_text = f"🔴 ADMIN ACTION: {description}\n\n⚠️ This action may be irreversible."
            self._overlay.show_permission_popup(
                text=confirm_text,
                on_approve=lambda: self._on_approved(intent, description, on_approved),
                on_deny=lambda: self._on_denied(intent, description, on_denied),
                timeout_ms=20000,
                is_admin=True
            )
        else:
            log_action(intent, {}, "denied_no_overlay", "admin")
            if on_denied:
                on_denied()

    def _on_approved(self, intent: str, description: str, callback: callable):
        """Handle approved permission."""
        log_action(intent, {}, "approved", "confirm")
        if self._voice:
            self._voice.play_confirm_beep()
        callback()

    def _on_denied(self, intent: str, description: str, callback: callable = None):
        """Handle denied permission."""
        log_action(intent, {}, "denied", "confirm")
        if self._voice:
            self._voice.speak("Cancelled.")
        if callback:
            callback()

    def approve_by_voice(self, text: str) -> bool:
        """Check if voice text is an approval. Returns True for yes-like responses."""
        text_lower = text.lower().strip()
        approvals = [
            "yes", "yeah", "yep", "yup", "sure", "do it", "go ahead",
            "confirmed", "confirm", "approve", "okay", "ok", "affirmative",
            "proceed", "execute", "run it", "yes please", "go for it",
        ]
        return any(a in text_lower for a in approvals)

    def deny_by_voice(self, text: str) -> bool:
        """Check if voice text is a denial."""
        text_lower = text.lower().strip()
        denials = [
            "no", "nope", "nah", "cancel", "stop", "don't", "abort",
            "negative", "deny", "never", "no way", "forget it",
        ]
        return any(d in text_lower for d in denials)
