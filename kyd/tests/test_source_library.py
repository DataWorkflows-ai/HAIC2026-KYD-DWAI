"""The source library behind the Sources tab and SOURCES.md."""
import csv
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[2]


def test_source_library_covers_every_db_source():
    rows = TestClient(app).get("/api/source-library").json()
    assert len(rows) >= 20 and all(r["url"].startswith("https://") for r in rows)
    urls = {r["url"] for r in rows}
    import sqlite3
    c = sqlite3.connect(f"file:{ROOT / 'kyd' / 'data' / 'kyd.sqlite'}?mode=ro", uri=True)
    db_urls = {u for (u,) in c.execute("SELECT url FROM source")}
    assert db_urls <= urls, db_urls - urls


def test_sources_md_in_sync():
    rows = list(csv.DictReader((ROOT / "kyd" / "data" / "sources.csv").open(encoding="utf-8")))
    md = (ROOT / "SOURCES.md").read_text(encoding="utf-8")
    assert all(r["url"] in md for r in rows)
