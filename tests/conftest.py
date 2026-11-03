import os

import pytest
from fastapi import Request

# app.db reads DATABASE_URL at import and crashes without it. The tests never
# open the pool (TestClient without "with" skips the lifespan), so a harmless
# dummy value is enough. CI has no .env and needs no secret.
os.environ.setdefault("DATABASE_URL", "postgresql://app:unused@localhost:5432/appdb")

# imported after DATABASE_URL is set
from app import auth
from app.main import app

USER = {"id": 1, "email": "demo@sobaoduong.local", "display_name": "Tài khoản dùng thử"}


def signed_in_page(request: Request):
    request.state.user = USER
    return USER


@pytest.fixture(autouse=True)
def signed_in():
    """Every test runs as user 1 unless it asks for signed_out (tests/test_auth.py)."""
    app.dependency_overrides[auth.current_user] = lambda: USER
    app.dependency_overrides[auth.page_user] = signed_in_page
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def signed_out():
    app.dependency_overrides.clear()
