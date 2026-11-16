"""Shareable path links serve the app; other unknown paths stay 404."""
from fastapi.testclient import TestClient

from app.main import app


def test_path_links():
    c = TestClient(app)
    for p in ("/house-22", "/house-22/map", "/senate-12/rankings", "/state", "/hd-5"):
        r = c.get(p)
        assert r.status_code == 200 and "<html" in r.text.lower(), p
    assert c.get("/not-a-page").status_code == 404
    assert c.get("/api/health").json()["ok"]
