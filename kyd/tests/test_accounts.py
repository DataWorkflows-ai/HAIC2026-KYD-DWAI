"""Accounts, the sign-in gate, saved chats, dashboards and document output (app/accounts.py, app/appstore.py).
Runs against SQLite here and against the Postgres app schema in the CI live-mode job."""
import asyncio
import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import appstore, security
from app.agent import orchestrator, system1, system2
from app.config import settings
from app.main import app
from app.security import Window

c = TestClient(app)
Q = "What is the uninsurance rate in house district 12?"


@pytest.fixture(autouse=True)
def no_login_limit(monkeypatch):
    monkeypatch.setattr(security, "LOGIN", Window(10_000, 60))


@pytest.fixture(scope="module", autouse=True)
def owner_email():
    s, before = settings(), settings().owner_email
    s.owner_email = f"boss-{uuid.uuid4().hex[:8]}@example.com"
    yield s.owner_email
    s.owner_email = before


def register(email=None, name="Test User", password="correct horse 1"):
    email = email or f"u-{uuid.uuid4().hex[:10]}@example.com"
    r = c.post("/api/auth/register", json={"email": email, "name": name, "password": password})
    assert r.status_code == 200, r.text
    return r.json()


def h(session):
    return {"Authorization": f"Bearer {session['token']}"}


@pytest.fixture(scope="module")
def owner(owner_email):
    if appstore.has_owner():
        pytest.skip("this database already has an owner")
    return register(owner_email, "Owner")


def test_register_login_and_me():
    s = register(password="pw-123456")
    assert s["user"]["role"] in ("user", "owner") and "pw_hash" not in s["user"]
    me = c.get("/api/auth/me", headers=h(s)).json()
    assert me["email"] == s["user"]["email"]
    assert c.post("/api/auth/login", json={"email": me["email"].upper(), "password": "pw-123456"}).status_code == 200
    assert c.post("/api/auth/login", json={"email": me["email"], "password": "wrong-pass"}).status_code == 401
    assert c.post("/api/auth/register", json={"email": me["email"], "name": "x", "password": "another-pw"}).status_code == 409
    assert c.post("/api/auth/register", json={"email": "not-an-email", "name": "x", "password": "another-pw"}).status_code == 422
    assert c.post("/api/auth/register", json={"email": "a@b.co", "name": "x", "password": "short"}).status_code == 422


def test_passwords_are_hashed():
    s = register(password="my secret words")
    row = appstore.user_by_email(s["user"]["email"])
    assert row["pw_hash"].startswith("scrypt$") and "my secret words" not in row["pw_hash"]


def test_sign_in_required_gate(monkeypatch):
    monkeypatch.setattr(settings(), "auth_required", True)
    assert c.get("/api/indicators").status_code == 401
    assert c.get("/api/chats").status_code == 401
    assert c.get("/api/health").status_code == 200
    s = register()
    assert c.get("/api/indicators", headers=h(s)).status_code == 200
    assert c.get("/api/indicators", headers={"Authorization": "Bearer forged.token"}).status_code == 401


def test_owner_assigns_roles_and_disables(owner):
    assert owner["user"]["role"] == "owner"
    u = register()
    uid = u["user"]["id"]
    assert c.post(f"/api/admin/users/{uid}", json={"role": "admin"}, headers=h(u)).status_code == 403
    assert c.get("/api/admin/usage", headers=h(u)).status_code == 403
    r = c.post(f"/api/admin/users/{uid}", json={"role": "admin"}, headers=h(owner))
    assert r.status_code == 200 and r.json()["role"] == "admin"
    assert c.get("/api/admin/usage", headers=h(u)).status_code == 200          # same token, new role
    assert c.post(f"/api/admin/users/{uid}", json={"role": "owner"}, headers=h(owner)).status_code == 422
    assert c.post(f"/api/admin/users/{owner['user']['id']}", json={"disabled": True}, headers=h(owner)).status_code == 400
    assert c.post(f"/api/admin/users/{uid}", json={"disabled": True}, headers=h(owner)).status_code == 200
    assert c.get("/api/auth/me", headers=h(u)).status_code == 401
    assert c.post("/api/auth/login", json={"email": u["user"]["email"], "password": "correct horse 1"}).status_code == 403


def test_second_owner_is_impossible(owner, owner_email):
    assert appstore.user_by_email(owner_email)["role"] == "owner"
    assert register()["user"]["role"] == "user"


def test_usage_counts_questions(owner):
    c.post("/api/agent/ask", json={"question": Q}, headers=h(owner))
    u = c.get("/api/admin/usage", headers=h(owner)).json()
    assert u["questions_today"] >= 1 and u["totals"]["users"] >= 1 and "llm_budget" in u
    assert all("query" not in r for r in u["recent"])


def test_chat_history_is_saved_and_private():
    a, b = register(), register()
    r = c.post("/api/agent/ask", json={"question": Q, "chat_id": "new"}, headers=h(a)).json()
    cid = r["chat_id"]
    assert cid and "[obs:" in r["text"]
    c.post("/api/agent/ask", json={"question": "And house district 13?", "chat_id": cid}, headers=h(a))
    chat = c.get(f"/api/chats/{cid}", headers=h(a)).json()
    assert [m["role"] for m in chat["messages"]] == ["user", "assistant", "user", "assistant"]
    assert chat["title"].startswith("What is the uninsurance") and chat["messages"][1]["content"]["route"] == "S1"
    assert c.get(f"/api/chats/{cid}", headers=h(b)).status_code == 404
    assert c.post("/api/agent/ask", json={"question": Q, "chat_id": cid}, headers=h(b)).status_code == 404
    assert c.get("/api/chats", headers=h(b)).json() == []


def test_chat_rename_pin_archive_search():
    a = register()
    ids = [c.post("/api/agent/ask", json={"question": q, "chat_id": "new"}, headers=h(a)).json()["chat_id"]
           for q in (Q, "Population of senate district 9?")]
    c.post(f"/api/chats/{ids[0]}", json={"title": "Uninsured HD12", "pinned": True}, headers=h(a))
    lst = c.get("/api/chats", headers=h(a)).json()
    assert lst[0]["id"] == ids[0] and lst[0]["pinned"] and lst[0]["title"] == "Uninsured HD12"
    assert [x["id"] for x in c.get("/api/chats", params={"q": "senate district 9"}, headers=h(a)).json()] == [ids[1]]
    c.post(f"/api/chats/{ids[1]}", json={"archived": True}, headers=h(a))
    assert [x["id"] for x in c.get("/api/chats", headers=h(a)).json()] == [ids[0]]
    assert [x["id"] for x in c.get("/api/chats", params={"archived": True}, headers=h(a)).json()] == [ids[1]]


def test_dashboard_saved_per_account():
    a, b = register(), register()
    assert c.get("/api/dashboard", headers=h(a)).json()["layout"] is None
    lay = {"widgets": [{"id": "w1", "type": "snapshot", "x": 0, "y": 0, "w": 4, "h": 4}]}
    assert c.post("/api/dashboard", json={"layout": lay}, headers=h(a)).status_code == 200
    lay["widgets"][0]["w"] = 6
    c.post("/api/dashboard", json={"layout": lay}, headers=h(a))
    assert c.get("/api/dashboard", headers=h(a)).json()["layout"] == lay
    assert c.get("/api/dashboard", headers=h(b)).json()["layout"] is None


def test_guest_gets_private_account_with_sample_chat(monkeypatch):
    monkeypatch.setattr(settings(), "auth_required", True)
    g1, g2 = (c.post("/api/auth/guest").json() for _ in range(2))
    assert g1["user"]["role"] == "user" and g1["user"]["email"].endswith("@guest.kyd") and g1["user"]["id"] != g2["user"]["id"]
    assert c.get("/api/indicators", headers=h(g1)).status_code == 200
    chats = c.get("/api/chats", headers=h(g1)).json()
    assert [x["title"] for x in chats] == ["Sample: House District 22 brief"]
    msgs = c.get(f"/api/chats/{chats[0]['id']}", headers=h(g1)).json()["messages"]
    doc = msgs[3]["content"]["document"]
    assert [m["role"] for m in msgs] == ["user", "assistant", "user", "assistant"] and msgs[1]["content"]["route"] == "S1"
    assert doc["title"] == "House District 22: one-page brief" and "[obs:" in doc["body"] and "Programs to raise" in doc["body"]
    assert c.get(f"/api/chats/{chats[0]['id']}", headers=h(g2)).status_code == 404
    assert chats[0]["id"] not in [x["id"] for x in c.get("/api/chats", headers=h(g2)).json()]


def test_split_document():
    text, doc = system2.split_document('Here is the memo.\n<document title="HD 12 brief">## Summary\n- one</document>')
    assert text == "Here is the memo." and doc == {"title": "HD 12 brief", "body": "## Summary\n- one"}
    assert system2.split_document("no document") == ("no document", None)


def test_document_figures_are_checked(monkeypatch):
    obs = [{"obs_id": "x1", "value": 12.3, "moe": 1.1, "label": "Uninsured", "indicator": "pct_uninsured",
            "geo_id": "HD-12", "unit": "pct", "vintage": "2020-2024", "source_id": "acs"}]
    async def fake_run(question, hint, history=None):
        assert history == [("earlier q", "earlier a")]
        return ('Summary.<document title="Brief">Uninsured: 12.3% [obs:x1]. Made up: 4,321 people.</document>',
                obs, [])
    monkeypatch.setattr(system1, "route", lambda q, g: SimpleNamespace(
        decision="S2", intent="profile", geo_ids=["HD-12"], reasons=[], places=[], refusal=None))
    monkeypatch.setattr(system2, "run", fake_run)
    monkeypatch.setattr(orchestrator, "settings", lambda: SimpleNamespace(llm_provider="anthropic"))
    a = asyncio.run(orchestrator.ask("write a brief", None, [("earlier q", "earlier a")]))
    assert a.document.title == "Brief" and "12.3%" in a.document.body
    assert "4,321" not in a.document.body and "unsupported_numbers_removed" in a.escalation_reasons
