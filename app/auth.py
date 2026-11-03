"""Accounts and sign-in (FR-23 → FR-25), with the standard library only.

Passwords: hashlib.scrypt with a random salt per user; the database stores "scrypt$<salt hex>$<hash hex>".
Sessions: the browser keeps a random token in an HttpOnly cookie; the database stores only its sha256,
so a leaked sessions table does not let anyone sign in.
"""

import hashlib
import hmac
import os
import secrets
import time
from collections import defaultdict, deque
from typing import Annotated

from fastapi import Depends, Request
from psycopg.rows import dict_row

from app import db
from app.errors import ApiError

COOKIE = "vml_session"
SESSION_DAYS = 30
DEMO_EMAIL = "demo@sobaoduong.local"
SECURE_COOKIE = os.getenv("APP_ENV", "development") == "production"  # Render serves HTTPS; localhost does not

SCRYPT = {"n": 2**14, "r": 8, "p": 1, "dklen": 32}

NOT_SIGNED_IN = ApiError(401, "NOT_SIGNED_IN", "Bạn cần đăng nhập để tiếp tục.")

USER_BY_TOKEN_SQL = """
SELECT u.id, u.email, u.display_name
FROM sessions s
JOIN users u ON u.id = s.user_id
WHERE s.token_hash = %(token_hash)s AND s.expires_at > now()
"""

INSERT_SESSION_SQL = """
INSERT INTO sessions (token_hash, user_id, expires_at)
VALUES (%(token_hash)s, %(user_id)s, now() + make_interval(days => %(days)s))
"""

DELETE_EXPIRED_SQL = "DELETE FROM sessions WHERE user_id = %(user_id)s AND expires_at <= now()"


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **SCRYPT)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt, digest = stored.split("$")
    except ValueError:  # "!" (the demo account) or anything else: no password can match
        return False
    if scheme != "scrypt":
        return False
    candidate = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), **SCRYPT)
    return hmac.compare_digest(candidate.hex(), digest)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def start_session(cur, user_id: int) -> str:
    """Store a new session and return the token for the cookie."""
    token = secrets.token_urlsafe(32)
    cur.execute(DELETE_EXPIRED_SQL, {"user_id": user_id})  # tidy up while we are here
    cur.execute(INSERT_SESSION_SQL, {"token_hash": token_hash(token), "user_id": user_id, "days": SESSION_DAYS})
    return token


def set_session_cookie(response, token: str) -> None:
    response.set_cookie(
        COOKIE, token, max_age=SESSION_DAYS * 86400, httponly=True, samesite="lax", secure=SECURE_COOKIE, path="/"
    )


def user_from_request(request: Request) -> dict | None:
    token = request.cookies.get(COOKIE)
    if not token:
        return None
    with db.pool.connection(timeout=5) as conn:
        return conn.cursor(row_factory=dict_row).execute(USER_BY_TOKEN_SQL, {"token_hash": token_hash(token)}).fetchone()


def current_user(request: Request) -> dict:
    """API dependency: the signed-in user, or 401 NOT_SIGNED_IN (app.js then opens the sign-in page)."""
    user = user_from_request(request)
    if user is None:
        raise NOT_SIGNED_IN
    return user


CurrentUser = Annotated[dict, Depends(current_user)]


class SignInRequired(Exception):
    """Raised by page_user; main.py answers with a redirect to /dang-nhap."""


def page_user(request: Request) -> dict:
    """Page dependency: the signed-in user (also put in request.state for base.html), or a redirect."""
    user = user_from_request(request)
    if user is None:
        raise SignInRequired
    request.state.user = user
    return user


# Brute-force guard: 5 wrong passwords for one email within 15 minutes locks that email for the rest of the window.
# shortcut: kept in memory, per running copy and reset on restart; use a table if the app runs several copies.
MAX_FAILURES = 5
WINDOW_SECONDS = 15 * 60
_failures: dict[str, deque] = defaultdict(deque)


def too_many_failures(email: str) -> bool:
    attempts = _failures[email]
    while attempts and attempts[0] < time.monotonic() - WINDOW_SECONDS:
        attempts.popleft()
    return len(attempts) >= MAX_FAILURES


def record_failure(email: str) -> None:
    _failures[email].append(time.monotonic())


def clear_failures(email: str) -> None:
    _failures.pop(email, None)
