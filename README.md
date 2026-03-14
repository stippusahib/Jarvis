# JARVIS: Just A Rather Very Intelligent System

### "It sees everything. Remembers nothing. Makes you superhuman."

A fully offline, privacy-first ambient AI desktop assistant for Windows 11.
It listens to the mic, reads the screen passively, thinks using a local LLM, and whispers
a proactive ≤15-word suggestion as a ghost HUD popup in the corner of the screen.

**Zero cloud. Zero disk. Zero trust required. Pull the WiFi cable — it still works.**

---

## One-Time Setup

1. Install **Ollama** → [https://ollama.ai/download](https://ollama.ai/download)
2. Open terminal: `ollama serve` (keep running in background)
3. Pull model: `ollama pull mistral`
4. Install deps: `py -3.11 -m pip install -r requirements.txt`

## Run

| Mode | Command |
|------|---------|
| Live (real mic + AI) | `py -3.11 main.py` |
| Demo (stage presentation) | `py -3.11 main.py --demo` |

## Privacy Proof (do this on stage)

1. Turn on **airplane mode** — visibly, in front of judges
2. Run `py -3.11 main.py` — works fully offline, no network needed
3. Open **Task Manager → Performance → Disk** — shows 0 write activity
4. Say: *"It heard everything. Stored nothing. Helped anyway."*

## Pipeline

```
Mic audio → Faster-Whisper tiny (offline) → RAM only
Screen    → MSS capture → Pillow resize → RAM only
Both      → Mistral 7B via Ollama (127.0.0.1) → ≤15 word suggestion
Output    → Ghost HUD overlay → 200ms fade in → 4s hold → 300ms fade out → RAM wiped
```

## Privacy Architecture

- All audio stored in `io.BytesIO` — never touches disk
- Screen frames stored in `io.BytesIO` — never touches disk
- `del + gc.collect()` called after every pipeline stage
- Ollama runs at `127.0.0.1` — zero external network calls
- `privacy_audit()` scans codebase at startup and confirms zero disk writes

## Tech Stack

- **Whisper** (faster-whisper tiny) — speech-to-text, offline, CUDA auto-detected
- **MSS** — lightweight screen capture
- **Ollama + Mistral 7B** — local LLM inference at `127.0.0.1`
- **Tkinter** — ghost overlay HUD with fade animations
- **pystray** — system tray integration

## License

MIT
