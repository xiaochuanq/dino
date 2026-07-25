import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Make lib/ modules importable exactly as they are on the Pico (flat names),
# and the repo root so tests can import config.py.
sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(ROOT))
