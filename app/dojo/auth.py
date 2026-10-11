"""Token/session primitives and the require_auth / require_role decorators."""
from __future__ import annotations

import functools
import hashlib
import secrets

from flask import g, request

from . import time_utils as tu
from .db import get_db
from .errors import ApiError, unauthenticated, forbidden

TOKEN_TTL_SECONDS = 600  # REQ-AUTH-006: 10 minutes


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(conn, user_id: int) -> tuple[str, "object"]:
    token = generate_token()
    now = tu.now_utc()
    expires = now + __import__("datetime").timedelta(seconds=TOKEN_TTL_SECONDS)
    conn.execute(
        "INSERT INTO sessions (token_hash, user_id, created_at, expires_at) VALUES (?,?,?,?)",
        (hash_token(token), user_id, tu.to_db(now), tu.to_db(expires)),
    )
    return token, expires


def revoke_token(conn, token: str) -> None:
    conn.execute("DELETE FROM sessions WHERE token_hash=?", (hash_token(token),))


def revoke_all_sessions(conn, user_id: int) -> None:
    conn.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))


def revoke_all_sessions_except(conn, user_id: int, keep_token: str) -> None:
    conn.execute(
        "DELETE FROM sessions WHERE user_id=? AND token_hash<>?",
        (user_id, hash_token(keep_token)),
    )


def _extract_token() -> str | None:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    token = header[len("Bearer "):].strip()
    return token or None


def resolve_user(conn, token: str):
    """Return the users row for a valid, non-expired token, else None."""
    row = conn.execute(
        "SELECT s.expires_at, u.* FROM sessions s JOIN users u ON u.id = s.user_id "
        "WHERE s.token_hash = ?",
        (hash_token(token),),
    ).fetchone()
    if row is None:
        return None
    if tu.from_db(row["expires_at"]) <= tu.now_utc():
        return None
    return row


# Endpoints allowed while a user must change their password (REQ-AUTH-009).
PASSWORD_CHANGE_EXEMPT = {
    ("GET", "me"),
    ("POST", "change_password"),
    ("POST", "logout"),
}


def require_auth(exempt_name: str | None = None):
    """Decorator: populates g.user from the Bearer token, enforcing
    REQ-COM-007 steps 1-2. `exempt_name` marks an endpoint that remains
    usable while the account must change its password."""

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            token = _extract_token()
            if not token:
                raise unauthenticated()
            conn = get_db()
            user = resolve_user(conn, token)
            if user is None:
                raise unauthenticated()
            g.user = user
            g.token = token
            if user["must_change_password"] and exempt_name not in ("me", "change_password", "logout"):
                raise ApiError("PASSWORD_CHANGE_REQUIRED")
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def optional_auth(fn):
    """Decorator: populates g.user if a valid Bearer token is present,
    otherwise leaves it as None. Never raises for a missing/invalid token —
    used by endpoints the public catalog allows anyone to browse, which
    still personalise their response (e.g. in_wishlist) when signed in."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        g.user = None
        g.token = None
        token = _extract_token()
        if token:
            user = resolve_user(get_db(), token)
            if user is not None and not user["must_change_password"]:
                g.user = user
                g.token = token
        return fn(*args, **kwargs)

    return wrapper


def require_role(*roles):
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if g.user["role"] not in roles:
                raise forbidden()
            return fn(*args, **kwargs)

        return wrapper

    return decorator
