# JARVIS 
### *It sees everything. Remembers nothing. Makes you superhuman.*

**JARVIS** is a privacy-obsessed ambient AI for Windows 11. Most "AI assistants" are just skin-deep wrappers around cloud APIs that harvest your data. JARVIS is different. It's a local-first ghost HUD that listens to your mic and reads your screen to whisper proactive suggestions without ever touching your SSD or the internet.

**Zero cloud. Zero disk writes. Zero trust required. It works if you pull the WiFi cable.**

---

## 🚀 The Latest: Auto-Adapting AI
The new **Device Analyzer** means you don't have to guess which models your PC can handle. When you hit "Analyse Device," JARVIS benchmarks your VRAM, RAM, and CPU to instantly configure the engine:
- **RTX GPUs (6GB+ VRAM)**: High-fidelity Whisper `medium` + crisp screen captures.
- **Mid-Range / AMD**: Balanced Whisper `small` + optimized JPEG loop.
- **CPU-Only / Lightweight**: Whisper `tiny` + minimal footprint to keep your system fast.

*Don't have the models?* The dashboard handles the sync automatically with a clear progress bar. No more terminal wrestling.

## 🛠️ One-Time Setup
1. **Ollama**: Download and install from [ollama.ai](https://ollama.ai/download).
2. **Brain**: Run `ollama pull mistral` (or your preferred LLM).
3. **Run**: Keep `ollama serve` alive in the background and launch: `py -3.11 main.py`.

*Note: JARVIS now auto-installs its own Python dependencies (`faster-whisper`, `huggingface-hub`, etc.) on the first run if they're missing.*

## 🏗️ The Pipeline (100% RAM-Only)
The engine is a strict one-way street that never persists data to your disk:
1. **Mic** → Audio chunk → `faster-whisper` (Offline) → RAM.
2. **Screen** → MSS Capture → Pillow resize → RAM.
3. **Brain** → Local Mistral (via Ollama at `127.0.0.1`) → Response.
4. **Display** → Ghost HUD overlay → Fade-in (200ms) → Hold (4s) → Fade-out (300ms).
5. **Wipe** → `del` + `gc.collect()` nukes all buffers from memory.

## 🔒 The Privacy Proof
I designed this so you can prove it doesn't leak data:
1. Turn on **Airplane Mode**.
2. Run JARVIS. It stays 100% functional.
3. Open **Task Manager → Performance → Disk**. You'll see absolute 0% write activity while the engine is thinking.

## 💻 Tech Stack
- **Audio**: `faster-whisper` (CUDA/DirectML fallback).
- **Vision**: `MSS` + `Pillow` for screen parsing.
- **Logic**: `Ollama` + `Mistral 7B` (or `Llava` for vision tasks).
- **Interface**: `CustomTkinter` dashboard + `Tkinter` ghost overlay.
- **Control**: `pystray` system tray integration.

## License
MIT
