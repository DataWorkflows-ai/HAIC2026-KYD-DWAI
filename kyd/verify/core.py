"""Shared pieces for source verification: the Check record, the report, file fingerprints.

Status levels
  pass   the check held
  info   a cross-source comparison worth showing, with no pass/fail expectation
  warn   sources disagree beyond tolerance, or provenance is incomplete; a person should look
  fail   a format change, transcription error or internal inconsistency; figures built on
         this source must not be trusted until it is fixed
"""
from __future__ import annotations
import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
RAW = REPO / "data" / "raw"
PROCESSED = REPO / "data" / "processed"
MANIFEST = Path(__file__).resolve().parent / "manifest.json"
REPORT = REPO / "kyd" / "data" / "verification_report.json"
ORDER = {"fail": 0, "warn": 1, "info": 2, "pass": 3}


@dataclass
class Check:
    id: str                    # stable, e.g. "census.S1701.house.pct_identity"
    source: str                # source id from SOURCES
    kind: str                  # format | consistency | transcription | cross_source | provenance
    status: str                # pass | info | warn | fail
    detail: str
    expected: Any = None
    actual: Any = None
    location: str | None = None   # page, sheet, district… where the check looked


@dataclass
class Report:
    checks: list[Check] = field(default_factory=list)

    def add(self, *a, **k) -> Check:
        c = Check(*a, **k)
        self.checks.append(c)
        return c

    def ok(self, id, source, kind, detail, **k):
        return self.add(id, source, kind, "pass", detail, **k)

    def expect(self, cond: bool, id, source, kind, detail, *, fail_status="fail", **k) -> bool:
        self.add(id, source, kind, "pass" if cond else fail_status, detail, **k)
        return cond

    def summary(self) -> dict:
        s = {k: 0 for k in ORDER}
        for c in self.checks:
            s[c.status] += 1
        return s

    def to_json(self, sources: dict) -> dict:
        return {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "git_sha": _git_sha(), "summary": self.summary(), "sources": sources,
                "checks": [asdict(c) for c in sorted(self.checks, key=lambda c: (ORDER[c.status], c.id))]}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_sha() -> str | None:
    try:
        return subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, timeout=5).stdout.strip() or None
    except Exception:
        return None


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}


def close(a: float | None, b: float | None, tol: float) -> bool:
    return a is not None and b is not None and abs(a - b) <= tol


def rel_close(a: float | None, b: float | None, rel: float) -> bool:
    return a is not None and b is not None and abs(a - b) <= rel * max(abs(a), abs(b), 1e-9)
