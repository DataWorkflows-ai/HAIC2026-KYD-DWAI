"""Make `app` importable however pytest is started (from kyd/backend, kyd/ or the repo root)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
