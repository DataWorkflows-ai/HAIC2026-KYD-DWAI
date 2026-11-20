"""Reference files the app reads at run time, from one place.

sqlite / fixture mode: read from the repository, as before.
live mode: read from kyd.datafile in Postgres (loaded by etl/promote_to_postgres.py). If the database is not
reachable the fact repository falls back to the bundled SQLite file, and so does this module.
"""
from __future__ import annotations
import csv
import io
import json
import sqlite3
from functools import lru_cache
from pathlib import Path

from ..config import settings

# name → path relative to kyd/data. These are the files promote_to_postgres.py loads.
FILES: dict[str, str] = {
    "place_aliases.json": "place_aliases.json",
    "neighborhood_aliases.json": "neighborhood_aliases.json",
    "verification_report.json": "verification_report.json",
    "legislators.csv": "legislators.csv",
    "sources.csv": "sources.csv",
    "district_counties.json": "district_counties.json",
    "district_overlap.csv": "district_overlap.csv",
    "district_local.json": "district_local.json",
    "programs.json": "programs.json",
    "program_facts.csv": "program_facts.csv",
    "boundaries_meta.json": "boundaries_meta.json",
    "tract_district_crosswalk.csv": "tract_district_crosswalk.csv",
    "bg_district_crosswalk.csv": "bg_district_crosswalk.csv",
    "hpha_properties.csv": "../../data/raw/research/hpha/hpha_properties.csv",
}
# Precomputed from scripts/ at load time, so live mode does not parse the raw workbooks on the server.
COMPUTED = ("program_context_static.json", "tanf_underenrollment.json")


def disk_path(name: str) -> Path:
    return (settings().data_dir / FILES[name]).resolve()


def _pg():
    """The Postgres repository when live mode is actually serving from Postgres, else None."""
    if settings().data_mode != "live":
        return None
    from .repo import repo
    r = repo()
    return r if getattr(r, "backend", "") == "postgres" else None


@lru_cache(maxsize=1)
def _live_files() -> dict[str, str]:
    return {r["name"]: r["content"] for r in _pg()._q("SELECT name, content FROM kyd.datafile")}


def origin() -> str:
    """Where reference files come from in this process: 'postgres' or 'files'."""
    return "postgres" if _pg() is not None else "files"


def text(name: str) -> str | None:
    """File content, or None if it does not exist."""
    if _pg() is not None:
        return _live_files().get(name)
    if name not in FILES:
        return None
    p = disk_path(name)
    return p.read_text(encoding="utf-8") if p.exists() else None


def load_json(name: str, default=None):
    t = text(name)
    return default if t is None else json.loads(t)


def csv_rows(name: str) -> list[dict]:
    t = text(name)
    return [] if t is None else list(csv.DictReader(io.StringIO(t)))


@lru_cache(maxsize=1)
def breakdown_rows() -> list[dict]:
    """Every row of the `breakdown` table, in load order."""
    pg = _pg()
    if pg is not None:
        rows = pg._q("SELECT * FROM kyd.breakdown ORDER BY ord")
        for r in rows:
            r.pop("ord", None)
        return rows
    p = settings().data_dir / "kyd.sqlite"
    c = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in c.execute("SELECT * FROM breakdown")]
    except sqlite3.OperationalError:
        return []
    finally:
        c.close()
