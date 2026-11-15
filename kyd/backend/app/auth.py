"""Who is calling, and with which role (§8.1). Client-supplied headers are never trusted by default.

Two ways to establish identity:

1. Signed bearer tokens (default when KYD_AUTH_SECRET is set).
   `Authorization: Bearer <payload>.<signature>`, where payload is base64url JSON
   {"sub", "role", "exp"} and signature is HMAC-SHA256 over the payload with KYD_AUTH_SECRET.
   Mint one with:  python -m app.auth --sub "rep.hd22" --role legislator --days 30
   A bad or expired token is rejected with 401. No token means anonymous viewer.

2. A trusted SSO reverse proxy (KYD_TRUST_PROXY_HEADERS=true).
   The proxy authenticates the user and sets x-kyd-user / x-kyd-role. Only enable this when
   the API is reachable ONLY through that proxy and the proxy strips those headers from
   incoming client requests; otherwise anyone can claim any role.

With neither configured, every caller is an anonymous viewer, whatever headers it sends.
"""
from __future__ import annotations
import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass

from fastapi import HTTPException, Request

from .config import settings

ROLES = ("viewer", "staff", "legislator", "auditor", "admin")


@dataclass(frozen=True)
class Principal:
    user: str
    role: str

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
    secret = secret or settings().auth_secret
    if not secret:
        raise ValueError("KYD_AUTH_SECRET is not set")
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


def current_principal(req: Request) -> Principal:
    """FastAPI dependency. See the module docstring for the rules."""
    s = settings()
    authz = req.headers.get("authorization", "")
    if s.auth_secret and authz.lower().startswith("bearer "):
        return verify(authz[7:].strip(), s.auth_secret)
    if s.trust_proxy_headers and req.headers.get("x-kyd-user"):
        role = req.headers.get("x-kyd-role", "viewer")
        return Principal(req.headers["x-kyd-user"], role if role in ROLES else "viewer")
    return ANONYMOUS


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Mint a KYD bearer token (needs KYD_AUTH_SECRET).")
    ap.add_argument("--sub", required=True, help="user id, e.g. rep.hd22 or staff.jdoe")
    ap.add_argument("--role", required=True, choices=ROLES)
    ap.add_argument("--days", type=float, default=30)
    a = ap.parse_args()
    print(mint(a.sub, a.role, int(a.days * 86400)))
