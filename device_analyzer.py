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
    """Pick best Whisper model based on hardware. Prefers 'small' for CUDA."""
    if gpu['type'] in ('cuda', 'directml'):
        if gpu['vram_gb'] >= 4:
            return 'small', 'float16'   # Best balance — fast + accurate on GPU
        else:
            return 'tiny', 'float16'
    else:
        # CPU mode — use int8 quantization for speed
        if system['ram_gb'] >= 16:
            return 'small', 'int8'
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
    """Pick screen capture resolution, quality, and interval."""
    if gpu['type'] in ('cuda', 'rocm') and system['ram_gb'] >= 16:
        # High-end: crisp captures, fast interval
        return {'resolution': [1280, 720], 'jpeg_quality': 60, 'interval': 3}
    elif system['ram_gb'] >= 8:
        # Mid-range: balanced
        return {'resolution': [960, 540], 'jpeg_quality': 50, 'interval': 4}
    else:
        # Low-end: lightweight captures
        return {'resolution': [640, 360], 'jpeg_quality': 40, 'interval': 6}


def _get_performance_tier(gpu, system):
    """Classify the device into a tier for display."""
    if gpu['type'] in ('cuda', 'rocm') and gpu['vram_gb'] >= 6 and system['ram_gb'] >= 16:
        return '🟢 High Performance'
    elif gpu['type'] in ('cuda', 'rocm') and gpu['vram_gb'] >= 4:
        return '🟡 Balanced'
    elif system['ram_gb'] >= 8:
        return '🟠 Lightweight'
    else:
        return '🔴 Minimal'


def analyse(progress_callback=None):
    """Run full device analysis and return optimal config.
    
    progress_callback(msg): optional function to update UI with status messages.
    """
    def _report(msg):
        if progress_callback:
            progress_callback(msg)
        print(f'🔍 {msg}')

    _report('Detecting GPU...')
    gpu = _get_gpu_info()
    _report(f'GPU: {gpu["name"]} ({gpu["type"]})')

    _report('Checking CPU & RAM...')
    system = _get_system_info()
    _report(f'RAM: {system["ram_gb"]}GB, CPU: {system["cpu_cores"]} cores')

    whisper_model, compute_type = _pick_whisper_model(gpu, system)
    preferred, lightweight, vision = _pick_ollama_models(gpu, system)
    capture = _pick_capture_settings(gpu, system)
    tier = _get_performance_tier(gpu, system)

    # Pre-download Whisper model if not cached
    _report(f'Checking Whisper model: {whisper_model}...')
    try:
        # Ensure downloads are allowed
        os.environ.pop('HF_HUB_OFFLINE', None)
        from faster_whisper import WhisperModel
        _report(f'⬇️ Downloading Whisper {whisper_model} (if needed)...')
        _test = WhisperModel(whisper_model, device='cpu', compute_type='int8')
        del _test
        _report(f'✅ Whisper {whisper_model} ready')
    except Exception as e:
        _report(f'⚠️ Whisper download issue: {e}')

    profile = {
        'gpu_type': gpu['type'],
        'gpu_name': gpu['name'],
        'vram_gb': gpu['vram_gb'],
        'ram_gb': system['ram_gb'],
        'cpu_cores': system['cpu_cores'],
        'cpu_name': system['cpu_name'],
        'tier': tier,
        'whisper_model': whisper_model,
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

    _report(f'Done! Tier: {tier}')
    return profile


def get_profile():
    """Get saved device profile, or None if not analysed yet."""
    settings = settings_manager.load_settings()
    return settings.get('device_profile', None)
