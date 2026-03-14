# PRIVACY: RAM-only. Zero disk I/O.
import pathlib
import gc
from datetime import datetime, timedelta

SEARCH_PATHS = [
    pathlib.Path.home() / "Downloads",
    pathlib.Path.home() / "Desktop",
    pathlib.Path.home() / "Documents",
]

FILE_TRIGGERS = ["file", "document", "pdf", "sent", "shared", "report", "plan", "sheet", "read the", "check the", "did you read", "did you check", "have you seen"]

def is_file_mention(text: str) -> bool:
    text_lower = text.lower()
    return any(trigger in text_lower for trigger in FILE_TRIGGERS)


def extract_keywords(text: str) -> list:
    words = text.lower().split()
    stopwords = ["file", "the", "and", "for", "you", "that", "this", "with", "have", "read", "sent", "check", "did", "your", "about"]
    return [w for w in words if len(w) >= 4 and w not in stopwords]


def find_recent_file(audio_text: str, hours: int = 48) -> pathlib.Path | None:
    keywords = extract_keywords(audio_text)
    if not keywords:
        return None

    cutoff = datetime.now() - timedelta(hours=hours)
    best_score = 0
    best_match = None

    for search_path in SEARCH_PATHS:
        try:
            if not search_path.exists():
                continue
            for filepath in search_path.iterdir():
                try:
                    if not filepath.is_file():
                        continue
                    
                    mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
                    if mtime < cutoff:
                        continue

                    if filepath.suffix.lower() not in [".pdf", ".txt", ".docx", ".doc", ".xlsx", ".csv", ".md"]:
                        continue

                    score = sum(1 for kw in keywords if kw in filepath.stem.lower())
                    if score > best_score:
                        best_score = score
                        best_match = filepath
                except Exception:
                    continue
        except Exception:
            continue

    return best_match if best_score > 0 else None
