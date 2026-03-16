# JARVIS 

### "It sees everything. Remembers nothing. Makes you superhuman."

I built JARVIS to be an ambient AI assistant for Windows 11 that actually respects your privacy. It listens to your mic, reads your screen passively, thinks using a local LLM, and whispers short, proactive suggestions via a ghost HUD overlay in the corner of your screen. 

No cloud. No disk writes. Pull your WiFi cable—it still works perfectly. 

---

## What's New: The Dashboard & Auto-Adapter

The latest version now ships with a sleek GUI dashboard and a smart **Device Analyzer**. You don't need to manually configure models or resolution settings anymore. 

When you click "Analyse Device," JARVIS looks at your VRAM, RAM, and CPU cores, then automatically scales its engine. Have an RTX 4090? You get the Whisper medium model and high-res screen captures. Running on a standard laptop CPU? It falls back to Whisper tiny and optimizes the capture loop to prevent lag. 

If you don't have the required AI models on your first run, the dashboard automatically syncs and downloads them directly to your HuggingFace cache with a live progress bar. 

## One-Time Setup

1. Install **Ollama** → [https://ollama.ai/download](https://ollama.ai/download)
2. Open your terminal and run `ollama serve` (keep this running in the background)
3. Pull the brain: `ollama pull mistral`
4. Run JARVIS: `py -3.11 main.py`

*Note: On your very first run, JARVIS will automatically pip-install `faster-whisper` and `huggingface-hub` if you don't have them, and download the optimal Whisper audio model for your hardware.*

## How to use it

Just run `py -3.11 main.py`. 

The GUI will launch and dock itself quietly in your system tray. Click the toggle to start the engine. You can click the "Models" panel to see exactly which Whisper model JARVIS picked for your machine, or switch to CLI mode if you prefer the raw logs. 

If you are demoing this (like on a stage), you can launch with `py -3.11 main.py --demo` to bypass the privacy audit delay. 

## The Privacy Proof (Try this yourself)

I hate apps that phone home with my data. So I designed this to prove it doesn't. 

1. Turn on **airplane mode** (do this visibly if you're showing it off). 
2. Start the engine from the JARVIS dashboard. It works entirely offline.
3. Open **Task Manager → Performance → Disk**. You will see exactly 0 bytes of write activity while the engine is running. 

## How it works under the hood

The pipeline is strictly RAM-to-RAM. 

1. **Audio**: The mic feeds into faster-whisper (running offline). 
2. **Vision**: It grabs your screen using MSS, resizes it with Pillow, and holds it in memory.
3. **Logic**: Both inputs hit Mistral 7B via your local Ollama instance (`127.0.0.1`). 
4. **Display**: The response triggers the ghost HUD overlay using Tkinter (200ms fade in, 4s hold, 300ms fade out). 
5. **Wipe**: Every frame and audio chunk is destroyed (`del` + `gc.collect()`) immediately after use. It never touches your SSD. 

## License

MIT
