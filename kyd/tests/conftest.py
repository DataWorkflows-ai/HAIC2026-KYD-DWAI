"""Make `app` importable however pytest is started (from kyd/backend, kyd/ or the repo root).

The data and agent tests call the API without signing in, so sign-in is not required here; test_accounts.py
turns it back on. Accounts go to a throwaway SQLite file (live mode uses the Postgres app schema)."""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
os.environ.setdefault("KYD_AUTH_REQUIRED", "false")
os.environ.setdefault("KYD_DATA_MODE", "sqlite")
os.environ.setdefault("KYD_APP_DB", str(Path(tempfile.mkdtemp(prefix="kyd-test-")) / "app.sqlite"))
