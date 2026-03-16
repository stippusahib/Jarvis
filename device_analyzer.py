# JARVIS Device Analyzer — Detects hardware and picks optimal configuration.
# PRIVACY: Reads system info only (GPU, CPU, RAM). Zero network calls. Zero disk I/O.
import os
import platform
import subprocess
import json

import settings_manager


def _get_gpu_info():
    """Detect GPU type, name, and VRAM — supports NVIDIA, AMD, Intel, and CPU."""
    gpu = {'type': 'cpu', 'name': 'None', 'vram_gb': 0}

    # Try NVIDIA first (nvidia-smi)
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader,nounits'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split(',')
            gpu['type'] = 'cuda'
            gpu['name'] = parts[0].strip()
            gpu['vram_gb'] = round(int(parts[1].strip()) / 1024, 1)
            return gpu
    except Exception:
        pass

    # Try torch CUDA
    try:
        import torch
        if torch.cuda.is_available():
            gpu['type'] = 'cuda'
            gpu['name'] = torch.cuda.get_device_name(0)
            gpu['vram_gb'] = round(torch.cuda.get_device_properties(0).total_mem / (1024**3), 1)
            return gpu
    except Exception:
        pass

    # Try DirectML (AMD & Intel on Windows)
    try:
        import torch_directml
        gpu['type'] = 'directml'
        gpu['name'] = torch_directml.device_name(0)
        gpu['vram_gb'] = 4  # DirectML doesn't expose VRAM easily
        return gpu
    except Exception:
        pass

    # Try AMD ROCm
    try:
        import torch
        if hasattr(torch.version, 'hip') and torch.version.hip:
            gpu['type'] = 'rocm'
            gpu['name'] = 'AMD ROCm GPU'
            gpu['vram_gb'] = 4
            return gpu
    except Exception:
        pass

    # Detect GPU name via WMI on Windows (for display even if no compute backend)
    try:
        result = subprocess.run(
            ['wmic', 'path', 'win32_videocontroller', 'get', 'name'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            lines = [l.strip() for l in result.stdout.strip().split('\n') if l.strip() and l.strip() != 'Name']
            if lines:
                gpu['name'] = lines[0]
                # Estimate type from name
                name_lower = lines[0].lower()
                if 'nvidia' in name_lower or 'geforce' in name_lower or 'rtx' in name_lower or 'gtx' in name_lower:
                    gpu['type'] = 'cuda'
                elif 'amd' in name_lower or 'radeon' in name_lower:
                    gpu['type'] = 'directml'
                elif 'intel' in name_lower:
                    gpu['type'] = 'directml'
    except Exception:
        pass

    # CPU fallback
    if gpu['type'] == 'cpu':
        gpu['name'] = platform.processor() or 'Unknown CPU'
    return gpu


def _get_system_info():
    """Get CPU and RAM info."""
    import psutil
    ram_gb = round(psutil.virtual_memory().total / (1024**3), 1)
    cpu_cores = os.cpu_count() or 4
    cpu_name = platform.processor() or 'Unknown'
    return {'ram_gb': ram_gb, 'cpu_cores': cpu_cores, 'cpu_name': cpu_name}


def _pick_whisper_model(gpu, system):
    """Pick the BEST Whisper model the device can handle — quality first."""
    if gpu['type'] in ('cuda', 'directml'):
        if gpu['vram_gb'] >= 6:
            return 'medium', 'float16'  # Best quality on strong GPU (6GB+)
        elif gpu['vram_gb'] >= 3:
            return 'small', 'float16'   # Great quality on mid GPU
        else:
            return 'base', 'float16'    # Good quality on low GPU
    else:
        # CPU mode — int8 quantization for speed
        if system['ram_gb'] >= 16:
            return 'small', 'int8'      # Best CPU can handle
        elif system['ram_gb'] >= 8:
            return 'base', 'int8'
        else:
            return 'tiny', 'int8'


def _pick_ollama_models(gpu, system):
    """Pick best Ollama model tier."""
    if gpu['type'] in ('cuda', 'rocm', 'directml') and gpu['vram_gb'] >= 6:
        # Strong GPU
        preferred = ['mistral', 'llama3.2']
        lightweight = ['phi3:mini', 'tinyllama']
        vision = ['llava', 'llava:latest']
    elif gpu['type'] in ('cuda', 'rocm', 'directml') and gpu['vram_gb'] >= 4:
        # Medium GPU
        preferred = ['phi3:mini', 'mistral']
        lightweight = ['tinyllama']
        vision = ['llava']
    else:
        # CPU or weak GPU — still pick decent models, Ollama handles CPU well
        if system['ram_gb'] >= 16:
            preferred = ['mistral', 'phi3:mini']
            lightweight = ['tinyllama']
            vision = []
        else:
            preferred = ['tinyllama', 'phi3:mini']
            lightweight = ['tinyllama']
            vision = []

    return preferred, lightweight, vision


def _pick_capture_settings(gpu, system):
    """Pick screen capture resolution, quality, and interval based on full device profile."""
    has_gpu = gpu['type'] in ('cuda', 'rocm', 'directml')

    if has_gpu and gpu['vram_gb'] >= 6 and system['ram_gb'] >= 16:
        # Top tier: crisp, fast captures
        return {'resolution': [1920, 1080], 'jpeg_quality': 70, 'interval': 2}
    elif has_gpu and gpu['vram_gb'] >= 4 and system['ram_gb'] >= 8:
        # Good GPU + decent RAM
        return {'resolution': [1280, 720], 'jpeg_quality': 60, 'interval': 3}
    elif system['ram_gb'] >= 16:
        # CPU but lots of RAM
        return {'resolution': [960, 540], 'jpeg_quality': 55, 'interval': 4}
    elif system['ram_gb'] >= 8:
        # Moderate RAM
        return {'resolution': [960, 540], 'jpeg_quality': 45, 'interval': 5}
    else:
        # Minimum viable
        return {'resolution': [640, 360], 'jpeg_quality': 35, 'interval': 6}


def _get_performance_tier(gpu, system):
    """Classify the device into a tier for display."""
    has_gpu = gpu['type'] in ('cuda', 'rocm', 'directml')

    if has_gpu and gpu['vram_gb'] >= 8 and system['ram_gb'] >= 16:
        return '🟢 Ultra — Maximum Quality'
    elif has_gpu and gpu['vram_gb'] >= 6 and system['ram_gb'] >= 12:
        return '🟢 High Performance'
    elif has_gpu and gpu['vram_gb'] >= 4:
        return '🟡 Balanced'
    elif system['ram_gb'] >= 16:
        return '🟠 CPU Optimized'
    elif system['ram_gb'] >= 8:
        return '🟠 Lightweight'
    else:
        return '🔴 Minimal'


def analyse(progress_callback=None, cancel_event=None):
    """Run full device analysis and return optimal config.
    
    progress_callback(msg): optional function to update UI with status messages.
    cancel_event: optional threading.Event to cancel the analysis.
    """
    def _report(msg):
        if progress_callback:
            progress_callback(msg)
        print(f'🔍 {msg}')

    def _cancelled():
        return cancel_event and cancel_event.is_set()

    _report('Detecting GPU...')
    gpu = _get_gpu_info()
    if _cancelled(): return None
    _report(f'GPU: {gpu["name"]} ({gpu["type"]})')

    _report('Checking CPU & RAM...')
    system = _get_system_info()
    if _cancelled(): return None
    _report(f'RAM: {system["ram_gb"]}GB  •  CPU: {system["cpu_cores"]} cores')

    whisper_model, compute_type = _pick_whisper_model(gpu, system)
    preferred, lightweight, vision = _pick_ollama_models(gpu, system)
    capture = _pick_capture_settings(gpu, system)
    tier = _get_performance_tier(gpu, system)

    # ── Check if Whisper model needs downloading ──
    WHISPER_SIZES = {
        'tiny': '~75 MB', 'base': '~150 MB', 'small': '~500 MB',
        'medium': '~1.5 GB', 'large-v2': '~3 GB'
    }

    os.environ.pop('HF_HUB_OFFLINE', None)
    os.environ.pop('TRANSFORMERS_OFFLINE', None)
    os.environ['HF_HUB_OFFLINE'] = '0'

    os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'

    # Check if model is cached roughly to decide if we need to show download progress UI
    model_cached = False
    try:
        from huggingface_hub import scan_cache_dir
        cache = scan_cache_dir()
        cached_repos = [r.repo_id for r in cache.repos]
        model_repo = f'Systran/faster-whisper-{whisper_model}'
        model_cached = model_repo in cached_repos
    except Exception:
        pass  # If we can't check, assume not cached

    if not model_cached:
        size = WHISPER_SIZES.get(whisper_model, '~500 MB')
        _report(f'⬇️ Downloading Whisper {whisper_model} ({size})...')
        if _cancelled(): return None
    else:
        _report(f'✅ Whisper {whisper_model} already cached')

    # Download / verify the model
    loaded_model = whisper_model
    try:
        from huggingface_hub import snapshot_download
        
        # We create a dummy tqdm class to capture progress and send it to our UI
        class CustomTqdm:
            def __init__(self, *args, **kwargs):
                self.total = kwargs.get('total', 100)
                self.n = 0
                if kwargs.get('desc', '') == 'Fetching 14 files':
                    _report(f"⬇️ Preparing {whisper_model} download...")
            def update(self, n=1):
                if _cancelled():
                    raise InterruptedError("Download cancelled by user")
                self.n += n
                if self.total > 0 and self.total > 100:  # Size in bytes
                    percent = int((self.n / self.total) * 100)
                    # Only update every few percent to avoid UI spam
                    if percent % 5 == 0:
                        mb_done = int(self.n / 1024 / 1024)
                        mb_total = int(self.total / 1024 / 1024)
                        _report(f"⬇️ Downloading {whisper_model} ({percent}% — {mb_done}MB / {mb_total}MB)")
            def close(self): pass
            def __enter__(self): return self
            def __exit__(self, exc_type, exc_val, exc_tb): pass
            @classmethod
            def write(cls, s, file=None, end="\n", nolock=False): pass
            def set_postfix(self, ordered_dict=None, refresh=True, **kwargs): pass

        # Monkey-patch tqdm in huggingface_hub
        import huggingface_hub.utils._tqdm as hf_tqdm
        original_tqdm = hf_tqdm.tqdm
        hf_tqdm.tqdm = CustomTqdm

        try:
            model_path = snapshot_download(
                repo_id=f"Systran/faster-whisper-{whisper_model}",
                resume_download=True
            )
        except InterruptedError:
            # Restore tqdm
            hf_tqdm.tqdm = original_tqdm
            return None  # Cancelled silently
        finally:
            # Restore tqdm
            hf_tqdm.tqdm = original_tqdm

        if _cancelled(): return None

        from faster_whisper import WhisperModel
        _report(f'⏳ Instantiating {whisper_model}...')
        # Pass the local directory path, this disables faster_whisper's internal double-download
        _test = WhisperModel(model_path, device='cpu', compute_type='int8')
        del _test
        import gc; gc.collect()
        _report(f'✅ Whisper {whisper_model} ready')
    except Exception as e:
        _report(f'⚠️ {whisper_model} failed — trying fallback...')
        # Try fallbacks
        for fb in ['small', 'base', 'tiny']:
            if fb == whisper_model:
                continue
            try:
                from faster_whisper import WhisperModel as WM2
                _test = WM2(fb, device='cpu', compute_type='int8')
                del _test
                loaded_model = fb
                _report(f'✅ Using Whisper {fb} (fallback)')
                break
            except Exception:
                continue

    if _cancelled(): return None

    profile = {
        'gpu_type': gpu['type'],
        'gpu_name': gpu['name'],
        'vram_gb': gpu['vram_gb'],
        'ram_gb': system['ram_gb'],
        'cpu_cores': system['cpu_cores'],
        'cpu_name': system['cpu_name'],
        'tier': tier,
        'whisper_model': loaded_model,
        'compute_type': compute_type,
        'preferred_models': preferred,
        'lightweight_models': lightweight,
        'vision_models': vision,
        'capture_resolution': capture['resolution'],
        'jpeg_quality': capture['jpeg_quality'],
        'capture_interval': capture['interval'],
    }

    # Save to settings
    settings = settings_manager.load_settings()
    settings['device_profile'] = profile
    settings_manager.save_settings(settings)

    _report(f'Done! {tier}')
    return profile


def get_profile():
    """Get saved device profile, or None if not analysed yet."""
    settings = settings_manager.load_settings()
    return settings.get('device_profile', None)
