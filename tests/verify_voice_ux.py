import os
import sys

# Project root path setup
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(ROOT_DIR)
os.environ["PYTHONPATH"] = ROOT_DIR

from apps.backend.voice_ux.tests.verify_voice_ux import run_verification

if __name__ == "__main__":
    run_verification()
