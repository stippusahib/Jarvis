# JARVIS Command Parser — Turns voice input into actionable intents.
# Pattern-based for speed, LLM fallback for complex commands.
import re


# ─── Intent Definitions ──────────────────────────────────────────────
# Each intent: (name, permission_tier, patterns)
# permission_tier: "auto", "confirm", "admin"

INTENT_PATTERNS = {
    # ── App Control ──────────────────────────────
    "open_app": {
        "tier": "auto",
        "patterns": [
            r"(?:open|launch|start|run|fire up|bring up)\s+(.+)",
        ],
        "examples": ["open Chrome", "launch VS Code", "start Spotify"],
    },
    "close_app": {
        "tier": "confirm",
        "patterns": [
            r"(?:close|exit|quit|kill|shut down|stop|end)\s+(.+)",
        ],
        "examples": ["close Chrome", "quit Notepad", "kill that app"],
    },
    "switch_app": {
        "tier": "auto",
        "patterns": [
            r"(?:switch to|go to|focus|alt tab to|show me)\s+(.+)",
        ],
        "examples": ["switch to Chrome", "go to VS Code"],
    },

    # ── Window Control ───────────────────────────
    "minimize_window": {
        "tier": "auto",
        "patterns": [
            r"(?:minimize|hide)\s*(?:this|the|current)?\s*(?:window)?",
            r"minimize\s+(.+)",
        ],
        "examples": ["minimize this", "minimize Chrome", "hide window"],
    },
    "maximize_window": {
        "tier": "auto",
        "patterns": [
            r"(?:maximize|fullscreen|full screen|make full)\s*(?:this|the|current)?\s*(?:window)?",
            r"maximize\s+(.+)",
        ],
        "examples": ["maximize this", "maximize Chrome", "fullscreen"],
    },
    "snap_left": {
        "tier": "auto",
        "patterns": [
            r"(?:snap|move|put)\s+(?:this\s+)?(?:window\s+)?(?:to\s+)?(?:the\s+)?left",
        ],
        "examples": ["snap left", "move window to left", "snap this left"],
    },
    "snap_right": {
        "tier": "auto",
        "patterns": [
            r"(?:snap|move|put)\s+(?:this\s+)?(?:window\s+)?(?:to\s+)?(?:the\s+)?right",
        ],
        "examples": ["snap right", "move window to right"],
    },
    "close_window": {
        "tier": "confirm",
        "patterns": [
            r"close\s+(?:this|the|current)\s+(?:window|tab)",
        ],
        "examples": ["close this window", "close the current tab"],
    },

    # ── File Operations ──────────────────────────
    "create_file": {
        "tier": "confirm",
        "patterns": [
            r"(?:create|make|new)\s+(?:a\s+)?(?:new\s+)?(?:file|document|folder|directory)\s*(?:called|named)?\s*(.*)",
        ],
        "examples": ["create a new file called notes.txt", "make a folder called project"],
    },
    "delete_file": {
        "tier": "admin",
        "patterns": [
            r"(?:delete|remove|trash|erase)\s+(?:the\s+)?(?:file|document|folder)?\s*(.+)",
        ],
        "examples": ["delete the file report.pdf", "remove old_backup folder"],
    },
    "move_file": {
        "tier": "confirm",
        "patterns": [
            r"(?:move|transfer)\s+(.+?)\s+(?:to|into)\s+(.+)",
        ],
        "examples": ["move report.pdf to Desktop", "move it to Documents"],
    },
    "copy_file": {
        "tier": "confirm",
        "patterns": [
            r"(?:copy|duplicate)\s+(.+?)\s+(?:to|into)\s+(.+)",
        ],
        "examples": ["copy report.pdf to Desktop"],
    },
    "rename_file": {
        "tier": "confirm",
        "patterns": [
            r"(?:rename)\s+(.+?)\s+(?:to|as)\s+(.+)",
        ],
        "examples": ["rename report.pdf to final_report.pdf"],
    },
    "open_file": {
        "tier": "auto",
        "patterns": [
            r"(?:open|show|display|view)\s+(?:the\s+)?(?:file\s+)?(.+\.[\w]+)",
        ],
        "examples": ["open report.pdf", "show the file notes.txt"],
    },
    "search_file": {
        "tier": "auto",
        "patterns": [
            r"(?:find|search|locate|where is|look for)\s+(?:my\s+)?(?:the\s+)?(?:file\s+)?(.+)",
        ],
        "examples": ["find my resume", "search for report.pdf", "where is the PDF"],
    },

    # ── System Control ───────────────────────────
    "volume_up": {
        "tier": "auto",
        "patterns": [
            r"(?:turn up|increase|raise|louder|volume up)\s*(?:the\s+)?(?:volume)?",
            r"(?:volume|sound)\s+up",
        ],
        "examples": ["turn up the volume", "volume up", "louder"],
    },
    "volume_down": {
        "tier": "auto",
        "patterns": [
            r"(?:turn down|decrease|lower|quieter|volume down)\s*(?:the\s+)?(?:volume)?",
            r"(?:volume|sound)\s+down",
        ],
        "examples": ["turn down the volume", "volume down", "quieter"],
    },
    "set_volume": {
        "tier": "auto",
        "patterns": [
            r"(?:set|change)\s+(?:the\s+)?volume\s+(?:to\s+)?(\d+)",
        ],
        "examples": ["set volume to 50", "change volume to 80"],
    },
    "mute": {
        "tier": "auto",
        "patterns": [
            r"(?:mute|silence|shut up|be quiet)\s*(?:the\s+)?(?:volume|sound|audio)?",
        ],
        "examples": ["mute", "silence", "mute the volume"],
    },
    "unmute": {
        "tier": "auto",
        "patterns": [
            r"(?:unmute|restore sound|turn on sound|unmute audio)",
        ],
        "examples": ["unmute", "restore sound"],
    },
    "play_pause": {
        "tier": "auto",
        "patterns": [
            r"(?:play|pause|resume|stop|toggle)\s*(?:the\s+)?(?:music|media|video|song)?",
        ],
        "examples": ["pause music", "play", "resume video", "pause"],
    },
    "next_track": {
        "tier": "auto",
        "patterns": [
            r"(?:next|skip|forward)\s*(?:the\s+)?(?:track|song|media|video)?",
        ],
        "examples": ["next song", "skip track", "next"],
    },
    "prev_track": {
        "tier": "auto",
        "patterns": [
            r"(?:previous|last|back|rewind)\s*(?:the\s+)?(?:track|song|media|video)?",
        ],
        "examples": ["previous song", "last track", "go back"],
    },
    "set_brightness": {
        "tier": "auto",
        "patterns": [
            r"(?:set|change)\s+(?:the\s+)?brightness\s+(?:to\s+)?(\d+)",
            r"brightness\s+(?:to\s+)?(\d+)",
        ],
        "examples": ["set brightness to 50", "brightness 80"],
    },
    "brightness_up": {
        "tier": "auto",
        "patterns": [
            r"(?:increase|turn up|raise|brighter)\s*(?:the\s+)?(?:brightness|screen)",
            r"brightness\s+up",
        ],
        "examples": ["increase brightness", "brighter"],
    },
    "brightness_down": {
        "tier": "auto",
        "patterns": [
            r"(?:decrease|turn down|lower|dimmer|dim)\s*(?:the\s+)?(?:brightness|screen)",
            r"brightness\s+down",
        ],
        "examples": ["decrease brightness", "dimmer", "dim screen"],
    },
    "screenshot": {
        "tier": "auto",
        "patterns": [
            r"(?:take|capture|grab|save)\s+(?:a\s+)?(?:screen\s*shot|screen\s*capture|screen\s*grab|snap)",
            r"screen\s*shot",
        ],
        "examples": ["take a screenshot", "capture screenshot", "screenshot"],
    },
    "lock_screen": {
        "tier": "auto",
        "patterns": [
            r"(?:lock|lock screen|lock the screen|lock my (?:laptop|computer|pc))",
        ],
        "examples": ["lock screen", "lock my laptop"],
    },
    "shutdown": {
        "tier": "admin",
        "patterns": [
            r"(?:shut\s*down|power off|turn off)\s*(?:the\s+)?(?:laptop|computer|pc|system)?",
        ],
        "examples": ["shutdown", "shut down the laptop", "power off"],
    },
    "restart": {
        "tier": "admin",
        "patterns": [
            r"(?:restart|reboot|re-?start)\s*(?:the\s+)?(?:laptop|computer|pc|system)?",
        ],
        "examples": ["restart", "reboot the laptop"],
    },
    "sleep": {
        "tier": "confirm",
        "patterns": [
            r"(?:sleep|hibernate|put to sleep)\s*(?:the\s+)?(?:laptop|computer|pc|system)?",
        ],
        "examples": ["sleep", "put to sleep"],
    },
    "wifi_toggle": {
        "tier": "confirm",
        "patterns": [
            r"(?:turn|toggle|switch)\s+(?:on|off|the)\s*(?:the\s+)?(?:wi-?fi|wifi|internet|network)",
            r"(?:enable|disable)\s+(?:the\s+)?(?:wi-?fi|wifi|internet)",
        ],
        "examples": ["turn on WiFi", "disable WiFi", "toggle wifi"],
    },
    "bluetooth_toggle": {
        "tier": "confirm",
        "patterns": [
            r"(?:turn|toggle|switch)\s+(?:on|off|the)\s*(?:the\s+)?bluetooth",
            r"(?:enable|disable)\s+(?:the\s+)?bluetooth",
        ],
        "examples": ["turn on bluetooth", "disable bluetooth"],
    },

    # ── Keyboard/Mouse ───────────────────────────
    "type_text": {
        "tier": "confirm",
        "patterns": [
            r"(?:type|write|input|enter)\s+(.+)",
        ],
        "examples": ["type hello world", "write this email"],
    },
    "press_key": {
        "tier": "auto",
        "patterns": [
            r"(?:press|hit|tap)\s+((?:ctrl|alt|shift|win|enter|escape|tab|space|delete|backspace)[\s+\w]*)",
        ],
        "examples": ["press ctrl+s", "hit enter", "press escape"],
    },
    "scroll_down": {
        "tier": "auto",
        "patterns": [
            r"(?:scroll|page)\s+down",
        ],
        "examples": ["scroll down", "page down"],
    },
    "scroll_up": {
        "tier": "auto",
        "patterns": [
            r"(?:scroll|page)\s+up",
        ],
        "examples": ["scroll up", "page up"],
    },

    # ── Web ──────────────────────────────────────
    "web_search": {
        "tier": "auto",
        "patterns": [
            r"(?:search|google|look up|search for|google for|search the web for)\s+(.+)",
            r"(?:web search|internet search)\s+(.+)",
        ],
        "examples": ["search for Python tutorials", "Google this error"],
    },
    "open_url": {
        "tier": "auto",
        "patterns": [
            r"(?:open|go to|navigate to|visit)\s+(https?://\S+)",
            r"(?:open|go to|navigate to|visit)\s+([\w]+\.(?:com|org|net|io|dev|ai|co)\S*)",
        ],
        "examples": ["open google.com", "go to github.com"],
    },
}

# Words/phrases that indicate the user is giving a command vs. making conversation
COMMAND_INDICATORS = [
    "open", "close", "launch", "start", "run", "stop", "quit", "exit", "kill",
    "minimize", "maximize", "snap", "switch to", "go to", "focus",
    "create", "delete", "remove", "move", "copy", "rename", "find", "search",
    "turn up", "turn down", "volume", "brightness", "mute", "unmute",
    "screenshot", "lock", "shutdown", "restart", "sleep", "hibernate",
    "type", "write", "press", "scroll", "wifi", "bluetooth",
    "shut down", "power off", "reboot",
]


class ParsedCommand:
    """Represents a parsed voice command."""

    def __init__(self, intent: str, tier: str, params: dict, raw_text: str, confidence: float = 1.0):
        self.intent = intent        # e.g. "open_app"
        self.tier = tier            # "auto", "confirm", "admin"
        self.params = params        # e.g. {"app_name": "chrome"}
        self.raw_text = raw_text    # original voice text
        self.confidence = confidence

    def __repr__(self):
        return f"Command({self.intent}, tier={self.tier}, params={self.params})"


def is_command(text: str) -> bool:
    """Quick check: is this text a command or just conversation?"""
    text_lower = text.lower().strip()
    return any(indicator in text_lower for indicator in COMMAND_INDICATORS)


def parse(text: str) -> ParsedCommand | None:
    """Parse voice text into a structured command.
    Returns None if text is not a recognized command.
    """
    text_lower = text.lower().strip()

    # Remove common filler words
    text_clean = text_lower
    for filler in ["please", "can you", "could you", "would you", "i want you to",
                    "i need you to", "go ahead and", "just", "now", "right now",
                    "for me", "jarvis"]:
        text_clean = text_clean.replace(filler, "").strip()
    text_clean = re.sub(r'\s+', ' ', text_clean).strip()

    if not text_clean:
        return None

    # Try each intent's patterns
    for intent_name, intent_def in INTENT_PATTERNS.items():
        for pattern in intent_def["patterns"]:
            match = re.search(pattern, text_clean, re.IGNORECASE)
            if match:
                params = _extract_params(intent_name, match, text_clean)
                return ParsedCommand(
                    intent=intent_name,
                    tier=intent_def["tier"],
                    params=params,
                    raw_text=text,
                    confidence=0.9
                )

    # No pattern matched — check if it looks like a command
    if is_command(text_lower):
        # Return as unknown command — will be sent to LLM for interpretation
        return ParsedCommand(
            intent="unknown",
            tier="confirm",
            params={"text": text_clean},
            raw_text=text,
            confidence=0.5
        )

    return None


def _extract_params(intent: str, match: re.Match, text: str) -> dict:
    """Extract parameters from regex match based on intent type."""
    groups = match.groups()
    params = {}

    if intent in ("open_app", "close_app", "switch_app"):
        if groups:
            app_name = _clean_app_name(groups[0])
            params["target"] = app_name

    elif intent in ("minimize_window", "maximize_window"):
        if groups and groups[0]:
            params["target"] = groups[0].strip()

    elif intent in ("create_file",):
        if groups and groups[0]:
            params["name"] = groups[0].strip()

    elif intent in ("delete_file", "search_file", "open_file"):
        if groups and groups[0]:
            params["target"] = groups[0].strip()

    elif intent in ("move_file", "copy_file", "rename_file"):
        if len(groups) >= 2:
            params["source"] = groups[0].strip()
            params["destination"] = groups[1].strip()

    elif intent in ("set_volume", "set_brightness"):
        if groups:
            try:
                params["value"] = int(groups[0])
            except (ValueError, IndexError):
                params["value"] = 50

    elif intent == "type_text":
        if groups:
            params["text"] = groups[0].strip()

    elif intent == "press_key":
        if groups:
            params["keys"] = groups[0].strip()

    elif intent in ("web_search",):
        if groups:
            params["query"] = groups[0].strip()

    elif intent in ("open_url",):
        if groups:
            url = groups[0].strip()
            if not url.startswith("http"):
                url = "https://" + url
            params["url"] = url

    elif intent == "wifi_toggle":
        params["action"] = "on" if any(w in text for w in ["on", "enable"]) else "off"

    elif intent == "bluetooth_toggle":
        params["action"] = "on" if any(w in text for w in ["on", "enable"]) else "off"

    return params


def _clean_app_name(name: str) -> str:
    """Clean extracted app name — remove filler words."""
    name = name.strip()
    for suffix in ["app", "application", "program", "window", "browser",
                     "for me", "please", "now", "right now"]:
        if name.lower().endswith(suffix):
            name = name[:-(len(suffix))].strip()
    return name.strip()


def get_human_description(cmd: ParsedCommand) -> str:
    """Get a human-readable description of a command for permission dialogs."""
    intent = cmd.intent
    p = cmd.params

    descriptions = {
        "open_app": f"Open {p.get('target', 'application')}",
        "close_app": f"Close {p.get('target', 'application')}",
        "switch_app": f"Switch to {p.get('target', 'application')}",
        "minimize_window": f"Minimize {p.get('target', 'current window')}",
        "maximize_window": f"Maximize {p.get('target', 'current window')}",
        "snap_left": "Snap window to left",
        "snap_right": "Snap window to right",
        "close_window": "Close current window",
        "create_file": f"Create file: {p.get('name', '?')}",
        "delete_file": f"⚠️ DELETE: {p.get('target', '?')}",
        "move_file": f"Move {p.get('source', '?')} → {p.get('destination', '?')}",
        "copy_file": f"Copy {p.get('source', '?')} → {p.get('destination', '?')}",
        "rename_file": f"Rename {p.get('source', '?')} → {p.get('destination', '?')}",
        "open_file": f"Open {p.get('target', '?')}",
        "search_file": f"Search for: {p.get('target', '?')}",
        "volume_up": "Increase volume",
        "volume_down": "Decrease volume",
        "set_volume": f"Set volume to {p.get('value', '?')}%",
        "mute": "Mute audio",
        "unmute": "Unmute audio",
        "set_brightness": f"Set brightness to {p.get('value', '?')}%",
        "brightness_up": "Increase brightness",
        "brightness_down": "Decrease brightness",
        "screenshot": "Take a screenshot",
        "lock_screen": "Lock screen",
        "shutdown": "⚠️ SHUTDOWN the computer",
        "restart": "⚠️ RESTART the computer",
        "sleep": "Put computer to sleep",
        "wifi_toggle": f"Turn WiFi {p.get('action', 'off')}",
        "bluetooth_toggle": f"Turn Bluetooth {p.get('action', 'off')}",
        "type_text": f"Type: \"{p.get('text', '?')[:30]}...\"",
        "press_key": f"Press {p.get('keys', '?')}",
        "scroll_down": "Scroll down",
        "scroll_up": "Scroll up",
        "web_search": f"Search: {p.get('query', '?')}",
        "open_url": f"Open: {p.get('url', '?')}",
    }

    return descriptions.get(intent, f"Execute: {intent}")
