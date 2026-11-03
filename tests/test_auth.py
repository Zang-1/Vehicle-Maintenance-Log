import pytest
from fastapi.testclient import TestClient
from psycopg.errors import UniqueViolation

from app import auth
from app.main import app
from app.routers.auth import safe_next
from tests.fakedb import use_fake_db

client = TestClient(app)


def browser_with(token):
    """A fresh client holding only this session cookie (the shared client keeps cookies from earlier logins)."""
    return TestClient(app, cookies={auth.COOKIE: token})

STORED = {"id": 5, "email": "lan@gmail.com", "display_name": "Lan", "password_hash": auth.hash_password("matkhau123")}


@pytest.fixture(autouse=True)
def no_lockouts():
    auth._failures.clear()
    yield
    auth._failures.clear()


# ---------- passwords and tokens ----------

def test_password_hash_is_salted_and_verifies():
    first, second = auth.hash_password("matkhau123"), auth.hash_password("matkhau123")
    assert first != second  # a new salt each time
    assert "matkhau123" not in first
    assert auth.verify_password("matkhau123", first)
    assert not auth.verify_password("matkhau124", first)


def test_demo_account_has_no_usable_password():
    assert not auth.verify_password("", "!")
    assert not auth.verify_password("anything", "!")


def test_only_the_token_hash_is_stored(monkeypatch):
    cursor = use_fake_db(monkeypatch, [])
    token = auth.start_session(cursor, 5)
    stored = cursor.calls_matching("INSERT INTO sessions")[0]
    assert stored["token_hash"] == auth.token_hash(token) != token
    assert stored["days"] == 30


# ---------- register ----------

def test_register_creates_the_user_and_signs_in(monkeypatch):
    cursor = use_fake_db(monkeypatch, [("INSERT INTO users", {"id": 5, "email": "lan@gmail.com", "display_name": "Lan"})])
    r = client.post("/api/auth/register", json={"email": "  Lan@Gmail.com ", "display_name": " Lan ", "password": "matkhau123"})
    assert r.status_code == 201
    assert r.json() == {"id": 5, "email": "lan@gmail.com", "display_name": "Lan"}
    sent = cursor.calls_matching("INSERT INTO users")[0]
    assert sent["email"] == "lan@gmail.com"  # BR-11: stored in lower case
    assert auth.verify_password("matkhau123", sent["password_hash"])
    cookie = r.headers["set-cookie"]
    assert cookie.startswith("vml_session=") and "HttpOnly" in cookie and "SameSite=lax" in cookie


def test_register_with_a_taken_email_is_409(monkeypatch):
    use_fake_db(monkeypatch, [("INSERT INTO users", UniqueViolation())])
    r = client.post("/api/auth/register", json={"email": "lan@gmail.com", "display_name": "Lan", "password": "matkhau123"})
    assert r.status_code == 409
    assert r.json()["error_code"] == "EMAIL_TAKEN"


@pytest.mark.parametrize(
    "body",
    [
        {"email": "lan@gmail.com", "display_name": "Lan", "password": "ngan"},  # BR-12: at least 8
        {"email": "khong-phai-email", "display_name": "Lan", "password": "matkhau123"},
        {"email": "lan@gmail.com", "display_name": "   ", "password": "matkhau123"},
    ],
)
def test_register_rejects_bad_input(monkeypatch, body):
    use_fake_db(monkeypatch, [])
    assert client.post("/api/auth/register", json=body).status_code == 422


# ---------- login ----------

def test_login_with_the_right_password(monkeypatch):
    use_fake_db(monkeypatch, [("FROM users WHERE email", STORED)])
    r = client.post("/api/auth/login", json={"email": "LAN@gmail.com", "password": "matkhau123"})
    assert r.status_code == 200
    assert "password_hash" not in r.json()
    assert r.headers["set-cookie"].startswith("vml_session=")


@pytest.mark.parametrize("row", [STORED, None])  # wrong password, unknown email: the same answer
def test_wrong_login_says_the_same_for_both_cases(monkeypatch, row):
    use_fake_db(monkeypatch, [("FROM users WHERE email", row)])
    r = client.post("/api/auth/login", json={"email": "lan@gmail.com", "password": "sai-mat-khau"})
    assert r.status_code == 401
    assert r.json() == {"error_code": "WRONG_LOGIN", "message": "Email hoặc mật khẩu không đúng."}
    assert "set-cookie" not in r.headers


def test_five_wrong_passwords_lock_the_email(monkeypatch):
    use_fake_db(monkeypatch, [("FROM users WHERE email", STORED)])
    for _ in range(5):
        assert client.post("/api/auth/login", json={"email": "lan@gmail.com", "password": "sai"}).status_code == 401
    r = client.post("/api/auth/login", json={"email": "lan@gmail.com", "password": "matkhau123"})
    assert r.status_code == 429  # even the right password waits out the window


def test_demo_button_signs_in_to_the_demo_account(monkeypatch):
    cursor = use_fake_db(monkeypatch, [("FROM users WHERE email", {**STORED, "email": auth.DEMO_EMAIL, "password_hash": "!"})])
    r = client.post("/api/auth/demo")
    assert r.status_code == 200
    assert cursor.calls_matching("FROM users WHERE email")[0] == {"email": auth.DEMO_EMAIL}


# ---------- signed out ----------

def test_api_without_a_session_is_401(signed_out, monkeypatch):
    use_fake_db(monkeypatch, [])
    for path in ["/api/vehicles", "/api/stats/dashboard", "/api/diagnoses", "/api/auth/me"]:
        r = client.get(path)
        assert r.status_code == 401, path
        assert r.json()["error_code"] == "NOT_SIGNED_IN"


def test_an_expired_or_unknown_cookie_is_401(signed_out, monkeypatch):
    cursor = use_fake_db(monkeypatch, [("FROM sessions s", None)])
    r = browser_with("abc").get("/api/vehicles")
    assert r.status_code == 401
    assert cursor.calls_matching("FROM sessions s")[0] == {"token_hash": auth.token_hash("abc")}


def test_a_valid_cookie_is_the_user(signed_out, monkeypatch):
    use_fake_db(monkeypatch, [("FROM sessions s", {"id": 5, "email": "lan@gmail.com", "display_name": "Lan"})])
    r = browser_with("abc").get("/api/auth/me")
    assert r.json() == {"id": 5, "email": "lan@gmail.com", "display_name": "Lan"}


def test_pages_redirect_to_sign_in_and_come_back(signed_out, monkeypatch):
    use_fake_db(monkeypatch, [])
    r = client.get("/xe/1?tab=lich-su", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/dang-nhap?next=/xe/1%3Ftab%3Dlich-su"


def test_sign_in_pages_are_public(signed_out, monkeypatch):
    use_fake_db(monkeypatch, [])
    for path in ["/dang-nhap", "/dang-ky"]:
        r = client.get(path)
        assert r.status_code == 200, path
        assert 'id="auth-form"' in r.text
    assert client.get("/static/auth.js").status_code == 200


def test_logout_deletes_the_session_and_the_cookie(signed_out, monkeypatch):
    cursor = use_fake_db(monkeypatch, [])
    r = browser_with("abc").post("/api/auth/logout")
    assert r.status_code == 204
    assert cursor.calls_matching("DELETE FROM sessions")[0] == {"token_hash": auth.token_hash("abc")}
    assert 'vml_session=""' in r.headers["set-cookie"]


@pytest.mark.parametrize(
    ("asked", "expected"),
    [("/xe/1", "/xe/1"), ("//evil.com", "/"), ("https://evil.com", "/"), ("/\\evil.com", "/"), (None, "/")],
)
def test_next_never_leaves_the_site(asked, expected):
    assert safe_next(asked) == expected


# ---------- one user never reaches another user's data (FR-25) ----------

def test_another_users_vehicle_is_not_found(monkeypatch):
    cursor = use_fake_db(monkeypatch, [("WHERE v.id", None)])
    r = client.get("/api/vehicles/2")
    assert r.status_code == 404
    assert cursor.calls_matching("WHERE v.id")[0] == {"id": 2, "uid": 1}


def test_records_of_another_users_vehicle_are_not_found(monkeypatch):
    cursor = use_fake_db(monkeypatch, [("FROM vehicles WHERE id", None)])
    assert client.get("/api/vehicles/2/records").status_code == 404
    assert client.get("/api/vehicles/2/records.csv").status_code == 404
    assert cursor.calls_matching("FROM vehicles WHERE id")[0] == {"id": 2, "uid": 1}


def test_another_users_record_cannot_be_deleted(monkeypatch):
    cursor = use_fake_db(monkeypatch, [("DELETE FROM maintenance_records", None)])
    assert client.delete("/api/records/9").status_code == 404
    assert cursor.calls_matching("DELETE FROM maintenance_records")[0] == {"id": 9, "uid": 1}


def test_a_default_service_type_is_read_only(monkeypatch):
    builtin = {
        "id": 3, "name": "Thay bugi", "description": None, "applies_to": "ALL", "default_interval_km": 8000,
        "default_interval_months": 12, "is_active": True, "used_count": 0, "is_builtin": True,
    }
    cursor = use_fake_db(monkeypatch, [("FROM service_types WHERE id", builtin)])
    body = {"name": "Thay bugi", "applies_to": "ALL"}
    for response in [
        client.put("/api/service-types/3", json=body),
        client.patch("/api/service-types/3/active", json={"active": False}),
        client.delete("/api/service-types/3"),
    ]:
        assert response.status_code == 403
        assert response.json()["error_code"] == "BUILTIN_SERVICE_TYPE"
    assert not cursor.calls_matching("UPDATE service_types")
    assert not cursor.calls_matching("DELETE FROM service_types")


def test_a_personal_type_cannot_copy_a_default_name(monkeypatch):
    use_fake_db(monkeypatch, [("lower(name) = lower", {"?column?": 1})])
    r = client.post("/api/service-types", json={"name": "thay bugi", "applies_to": "ALL"})
    assert r.status_code == 409
    assert r.json()["error_code"] == "DUPLICATE_SERVICE_TYPE"


def test_diagnosis_history_is_per_user(monkeypatch):
    cursor = use_fake_db(monkeypatch, [("FROM diagnoses", [])])
    assert client.get("/api/diagnoses").json() == []
    assert cursor.calls_matching("FROM diagnoses")[0] == {"uid": 1}
