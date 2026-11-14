"""pytest entry point; the checks live in run_tests.py (also runnable without pytest)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from run_tests import *  # noqa: F401,F403,E402
