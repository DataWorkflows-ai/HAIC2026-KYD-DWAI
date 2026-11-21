"""Accounts (register, sign in), owner and admin pages, saved chats and dashboards. Storage: app/appstore.py."""
from __future__ import annotations
import logging
import re
import secrets
from collections import Counter
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from . import appstore, audit
from .agent import system1
from .agent.orchestrator import answer_s1
from .auth import ACCOUNT, Principal, check_password, current_principal, forget, hash_password, mint
from .config import settings
from .security import LLM_BUDGET

log = logging.getLogger("kyd.accounts")
auth_api = APIRouter(prefix="/api/auth")
api = APIRouter(prefix="/api")
Who = Depends(current_principal)
EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[A-Za-z]{2,}$")


class Register(BaseModel):
    email: str = Field(max_length=254)
    name: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=8, max_length=200)


class Login(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=200)


def public(u: dict) -> dict:
    return {k: u[k] for k in ("id", "email", "name", "role", "disabled", "created_at", "last_login") if k in u}


def _session(u: dict) -> dict:
    token = mint(ACCOUNT + u["id"], u["role"], int(settings().token_days * 86400))
    return {"token": token, "user": public(u)}


def account(who: Principal = Who) -> Principal:
    if not who.email:
        raise HTTPException(401, "sign in with an account", headers={"WWW-Authenticate": "Bearer"})
    return who


Me = Depends(account)


@auth_api.post("/register")
def register(body: Register):
    email = body.email.strip().lower()
    if not EMAIL.match(email):
        raise HTTPException(422, "enter a valid email address")
    if appstore.user_by_email(email):
        raise HTTPException(409, "an account with that email already exists; sign in instead")
    owner = settings().owner_email.strip().lower()
    role = "owner" if (email == owner if owner else not appstore.has_owner()) else "user"
    if role == "owner" and appstore.has_owner():
        role = "user"
    u = appstore.create_user(email, body.name.strip(), hash_password(body.password), role)
    appstore.touch_login(u["id"])
    audit.record(u["id"], role, "register")
    return _session(u)


GUEST_DOMAIN = "guest.kyd"
SAMPLE_GEO = "HD-22"


def _sample_chat(uid: str) -> None:
    """A starter chat with a document, built from rule-based (System 1) answers: no LLM call, every figure cited."""
    profile_q = "Give me a profile of House District 22"
    routes = [system1.route(q, SAMPLE_GEO) for q in (profile_q, "Which programs fit House District 22?")]
    if [r.intent for r in routes] != ["profile", "programs"]:
        return
    profile, programs = (answer_s1(r) for r in routes)
    brief_q = "Write a one-page brief on House District 22 for a constituent meeting"
    body = "\n\n".join([
        "## At a glance\n" + profile.text.split("\n", 1)[-1],
        "## Programs to raise\n" + programs.text.split("\n", 1)[-1],
        "## Notes\n- Figures are population-level estimates (ACS 2020–2024) with 90% margins of error.\n"
        "- Program fit reflects indicated need relative to the state; each agency determines eligibility.",
    ])
    brief = programs.model_copy(update={
        "text": "Here is a one-page brief built from the cited figures. It is open in the document panel.",
        "observations": profile.observations + programs.observations,
        "document": {"title": "House District 22: one-page brief", "body": body}})
    c = appstore.create_chat(uid, "Sample: House District 22 brief")
    for q, a in ((profile_q, profile), (brief_q, brief)):
        appstore.add_message(c["id"], "user", q)
        appstore.add_message(c["id"], "assistant", {**a.model_dump(mode="json"), "chat_id": c["id"]})


@auth_api.post("/guest")
def guest():
    """One click, no form: a private account for trying the demo. It has no usable password, so signing out
    ends access to it."""
    tag = secrets.token_hex(4)
    u = appstore.create_user(f"guest-{tag}@{GUEST_DOMAIN}", f"Guest {tag[:4].upper()}",
                             hash_password(secrets.token_urlsafe(24)), "user")
    appstore.touch_login(u["id"])
    try:
        _sample_chat(u["id"])
    except Exception:
        log.exception("sample chat for guest failed")
    audit.record(u["id"], "user", "guest")
    return _session(u)


@auth_api.post("/login")
def login(body: Login):
    u = appstore.user_by_email(body.email.strip())
    if not u or not check_password(body.password, u["pw_hash"]):
        raise HTTPException(401, "email or password is incorrect")
    if u["disabled"]:
        raise HTTPException(403, "this account is disabled; contact the owner")
    appstore.touch_login(u["id"])
    audit.record(u["id"], u["role"], "login")
    return _session(u)


@auth_api.get("/me")
def me(who: Principal = Me):
    return public(appstore.user_by_id(who.user))


# ── owner: accounts ───────────────────────────────────────────────────────
class UserUpdate(BaseModel):
    role: str | None = Field(default=None, pattern="^(admin|user)$")
    disabled: bool | None = None


@api.get("/admin/users")
def users(who: Principal = Me):
    who.require("owner", "admin")
    return [public(u) for u in appstore.list_users()]


@api.post("/admin/users/{uid}")
def update_user(uid: str, body: UserUpdate, who: Principal = Me):
    who.require("owner")
    u = appstore.user_by_id(uid)
    if not u:
        raise HTTPException(404, "unknown account")
    if u["role"] == "owner":
        raise HTTPException(400, "the owner account cannot be changed")
    appstore.update_user(uid, body.role, body.disabled)
    forget(uid)
    audit.record(who.user, who.role, "update_user", query=f"{uid} role={body.role} disabled={body.disabled}")
    return public(appstore.user_by_id(uid))


@api.get("/admin/usage")
def usage(who: Principal = Me):
    who.require("owner", "admin")
    rows = audit.recent(days=7)
    names = {u["id"]: u["email"] for u in appstore.list_users()}
    today = datetime.now(timezone.utc).date().isoformat()
    asks = [r for r in rows if r["action"] == "agent_ask"]
    by_day = Counter(r["ts"][:10] for r in asks)
    by_user = Counter(r["actor"] for r in asks)
    return {
        "totals": appstore.counts(),
        "questions_today": by_day.get(today, 0),
        "questions_by_day": [{"day": d, "questions": n} for d, n in sorted(by_day.items())],
        "by_user": [{"user": names.get(a, a), "questions": n} for a, n in by_user.most_common(20)],
        "routes": dict(Counter(r["route"] or "n/a" for r in asks)),
        "llm_budget": LLM_BUDGET.status(),
        "recent": [{"ts": r["ts"], "user": names.get(r["actor"], r["actor"]), "action": r["action"],
                    "route": r["route"]} for r in rows[:40]],
    }


# ── chats ─────────────────────────────────────────────────────────────────
class ChatUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    pinned: bool | None = None
    archived: bool | None = None


@api.get("/chats")
def chats(archived: bool = False, q: str = "", who: Principal = Me):
    return appstore.list_chats(who.user, archived, q.strip()[:100])


@api.get("/chats/{cid}")
def chat(cid: str, who: Principal = Me):
    c = appstore.get_chat(who.user, cid)
    if not c:
        raise HTTPException(404, "unknown chat")
    return {**c, "messages": appstore.messages(cid)}


@api.post("/chats/{cid}")
def update_chat(cid: str, body: ChatUpdate, who: Principal = Me):
    if not appstore.get_chat(who.user, cid):
        raise HTTPException(404, "unknown chat")
    appstore.update_chat(who.user, cid, body.title, body.pinned, body.archived)
    return appstore.get_chat(who.user, cid)


def chat_for_question(who: Principal, chat_id: str | None, question: str) -> dict | None:
    """The chat a question belongs to: the caller's chat_id, or a new one titled by the question ("new")."""
    if not who.email or chat_id is None:
        return None
    if chat_id == "new":
        title = " ".join(question.split())
        return appstore.create_chat(who.user, title[:80] + ("…" if len(title) > 80 else ""))
    c = appstore.get_chat(who.user, chat_id)
    if not c:
        raise HTTPException(404, "unknown chat")
    return c


def history(chat_id: str, turns: int = 3) -> list[tuple[str, str]]:
    """The last few (question, answer text) pairs, for follow-up questions."""
    ms = appstore.messages(chat_id)
    pairs = [(a["content"], b["content"].get("text", "")) for a, b in zip(ms, ms[1:])
             if a["role"] == "user" and b["role"] == "assistant"]
    return pairs[-turns:]


# ── dashboard ─────────────────────────────────────────────────────────────
class Dashboard(BaseModel):
    layout: dict


@api.get("/dashboard")
def dashboard(who: Principal = Me):
    return appstore.get_dashboard(who.user) or {"layout": None, "updated_at": None}


@api.post("/dashboard")
def save_dashboard(body: Dashboard, who: Principal = Me):
    if len(str(body.layout)) > 200_000:
        raise HTTPException(413, "dashboard is too large")
    return {"updated_at": appstore.save_dashboard(who.user, body.layout)}
