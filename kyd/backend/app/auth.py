"""Who is calling, and with which role (§8.1). Client-supplied headers are never trusted by default.

Two ways to establish identity:

1. Signed bearer tokens.
   `Authorization: Bearer <payload>.<signature>`, where payload is base64url JSON
   {"sub", "role", "exp"} and signature is HMAC-SHA256 over the payload with KYD_AUTH_SECRET
   (a random per-process key when that is unset, so tokens end at every restart).
   Accounts (app/accounts.py) get tokens with sub "acct:<id>"; their role and disabled flag are re-read from the
   account store, so a change applies without signing in again.
   Service tokens: python -m app.auth --sub "eval.bot" --role staff --days 1
   A bad or expired token is rejected with 401. No token means anonymous viewer.

2. A trusted SSO reverse proxy (KYD_TRUST_PROXY_HEADERS=true).
   The proxy authenticates the user and sets x-kyd-user / x-kyd-role. Only enable this when
   the API is reachable ONLY through that proxy and the proxy strips those headers from
   incoming client requests; otherwise anyone can claim any role.

With KYD_AUTH_REQUIRED (the default), anonymous callers get 401 from every /api route except /api/health and
/api/auth/*.
"""
from __future__ import annotations
import base64
import hashlib
import hmac
import json
import secrets
import threading
import time
from dataclasses import dataclass

from fastapi import HTTPException, Request

from . import appstore
from .config import settings

ROLES = ("viewer", "user", "staff", "legislator", "auditor", "admin", "owner")
ACCOUNT_ROLES = ("user", "admin", "owner")
ACCOUNT = "acct:"                                  # token sub prefix for app accounts
_EPHEMERAL = secrets.token_urlsafe(32)


def signing_secret() -> str:
    return settings().auth_secret or _EPHEMERAL


def secret_status() -> str:
    return "configured" if settings().auth_secret else "ephemeral"


@dataclass(frozen=True)
class Principal:
    user: str
    role: str
    email: str = ""
    name: str = ""

    def require(self, *roles: str) -> None:
        if self.role not in roles:
            raise HTTPException(403, f"{' or '.join(roles)} role required")


ANONYMOUS = Principal("anonymous", "viewer")


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _sign(payload: str, secret: str) -> str:
    return _b64(hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest())


def mint(sub: str, role: str, ttl_seconds: int = 30 * 86400, secret: str | None = None) -> str:
    if role not in ROLES:
        raise ValueError(f"role must be one of {ROLES}")
    secret = secret or signing_secret()
    payload = _b64(json.dumps({"sub": sub, "role": role, "exp": int(time.time()) + ttl_seconds},
                              separators=(",", ":")).encode())
    return f"{payload}.{_sign(payload, secret)}"


def verify(token: str, secret: str) -> Principal:
    try:
        payload, sig = token.split(".")
        if not hmac.compare_digest(sig, _sign(payload, secret)):
            raise ValueError("bad signature")
        claims = json.loads(_unb64(payload))
        if claims["exp"] < time.time():
            raise ValueError("expired")
        if claims["role"] not in ROLES:
            raise ValueError("unknown role")
        return Principal(str(claims["sub"]), claims["role"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as e:
        raise HTTPException(401, f"invalid token: {e}", headers={"WWW-Authenticate": "Bearer"})


_cache: dict[str, tuple[float, dict | None]] = {}
_cache_lock = threading.Lock()
CACHE_SECONDS = 30


def forget(uid: str) -> None:
    with _cache_lock:
        _cache.pop(uid, None)


def _account(uid: str) -> dict | None:
    with _cache_lock:
        hit = _cache.get(uid)
    if hit and hit[0] > time.monotonic():
        return hit[1]
    u = appstore.user_by_id(uid)
    with _cache_lock:
        _cache[uid] = (time.monotonic() + CACHE_SECONDS, u)
    return u


def account_principal(uid: str) -> Principal:
    u = _account(uid)
    if not u or u["disabled"]:
        raise HTTPException(401, "account not found or disabled", headers={"WWW-Authenticate": "Bearer"})
    return Principal(uid, u["role"], u["email"], u["name"])


def current_principal(req: Request) -> Principal:
    """FastAPI dependency. See the module docstring for the rules."""
    s = settings()
    authz = req.headers.get("authorization", "")
    if authz.lower().startswith("bearer "):
        p = verify(authz[7:].strip(), signing_secret())
        return account_principal(p.user[len(ACCOUNT):]) if p.user.startswith(ACCOUNT) else p
    if s.trust_proxy_headers and req.headers.get("x-kyd-user"):
        role = req.headers.get("x-kyd-role", "viewer")
        return Principal(req.headers["x-kyd-user"], role if role in ROLES else "viewer")
    return ANONYMOUS


def signed_in(req: Request) -> None:
    """Router dependency: with KYD_AUTH_REQUIRED, every /api route but health needs a signed-in caller."""
    if settings().auth_required and req.url.path != "/api/health" and current_principal(req) is ANONYMOUS:
        raise HTTPException(401, "sign in required", headers={"WWW-Authenticate": "Bearer"})


# scrypt from the standard library: memory-hard, no extra dependency.
SCRYPT = (2 ** 14, 8, 1)


def hash_password(pw: str) -> str:
    n, r, p = SCRYPT
    salt = secrets.token_bytes(16)
    h = hashlib.scrypt(pw.encode(), salt=salt, n=n, r=r, p=p, dklen=32)
    return f"scrypt${n}${r}${p}${_b64(salt)}${_b64(h)}"


def check_password(pw: str, stored: str) -> bool:
    try:
        _, n, r, p, salt, h = stored.split("$")
        got = hashlib.scrypt(pw.encode(), salt=_unb64(salt), n=int(n), r=int(r), p=int(p), dklen=32)
        return hmac.compare_digest(got, _unb64(h))
    except (ValueError, TypeError):
        return False


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Mint a KYD bearer token (signed with KYD_AUTH_SECRET).")
    ap.add_argument("--sub", required=True, help="user id, e.g. rep.hd22 or staff.jdoe")
    ap.add_argument("--role", required=True, choices=ROLES)
    ap.add_argument("--days", type=float, default=30)
    a = ap.parse_args()
    print(mint(a.sub, a.role, int(a.days * 86400)))
