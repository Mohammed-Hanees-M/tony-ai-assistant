import importlib
import os

def validate_premium_voice_dependencies():
    """
    Ensures all required production dependencies for the premium voice stack are present.
    Raises RuntimeError if missing.
    """
    required = {
        "faster_whisper": "pip install faster-whisper",
        "sounddevice": "pip install sounddevice",
        "numpy": "pip install numpy",
        "pyaudio": "pip install pyaudio",
        "scipy": "pip install scipy"
    }
    
    missing = []
    for lib, install_cmd in required.items():
        try:
            importlib.import_module(lib)
        except ImportError:
            missing.append(f"{lib} (Install via: {install_cmd})")
            
    if missing:
        error_msg = "[FATAL] Missing Premium Voice Dependencies:\n- " + "\n- ".join(missing)
        raise RuntimeError(error_msg)

    # Validate ONNX Models (Piper)
    # This is a placeholder for actual model path checking logic
    # print("[SYSTEM] All premium voice dependencies validated.")
