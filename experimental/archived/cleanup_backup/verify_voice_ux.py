import os
import sys

# Project root path setup
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["PYTHONPATH"] = "."

from apps.backend.voice_ux.tests.verify_voice_ux import run_verification

if __name__ == "__main__":
    run_verification()
