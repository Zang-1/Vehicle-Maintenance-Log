from contextlib import contextmanager
from datetime import UTC, datetime

import psycopg
import pytest
from fastapi.testclient import TestClient

from app import ai, db
from app.main import app

client = TestClient(app)

SYMPTOM = "Phanh trước kêu rít khi bóp mạnh, tay phanh hơi sâu"


class FakeConnection:
    """Records every INSERT into diagnoses and answers the history query."""

    def __init__(self, saved, rows):
        self.saved = saved
        self.rows = rows

    def execute(self, query, params=None):
        if query.lstrip().startswith("INSERT INTO diagnoses"):
            self.saved.append(params)
        return self

    def cursor(self, row_factory=None):
        return self

    def fetchall(self):
        return self.rows


@pytest.fixture
def saved(monkeypatch):
    rows = []

    @contextmanager
    def connection(timeout=None):
        yield FakeConnection(rows, [])

    monkeypatch.setattr(db.pool, "connection", connection)
    return rows


def test_diagnose_returns_the_suggestion_and_saves_it(monkeypatch, saved):
    monkeypatch.setattr(ai, "summarize_safe", lambda text, **kw: "Má phanh mòn.\nMức khẩn cấp: MEDIUM")
    r = client.post("/diagnose", json={"symptom_text": SYMPTOM})
    assert r.status_code == 200
    assert r.json() == {"suggestion": "Má phanh mòn.\nMức khẩn cấp: MEDIUM"}
    assert saved == [{
        "user_id": 1, "vehicle_id": None, "symptom_text": SYMPTOM, "model": ai.AI_MODEL, "status": "OK", "error_code": None,
        "ai_suggestion": "Má phanh mòn.\nMức khẩn cấp: MEDIUM", "urgency_level": "MEDIUM",
    }]


def test_answer_without_urgency_line_is_saved_without_urgency(monkeypatch, saved):
    monkeypatch.setattr(ai, "summarize_safe", lambda text, **kw: "Nên mang xe tới gara kiểm tra.")
    client.post("/diagnose", json={"symptom_text": SYMPTOM})
    assert saved[0]["urgency_level"] is None


def test_symptom_is_trimmed_before_the_ai_call(monkeypatch, saved):
    seen = []
    monkeypatch.setattr(ai, "summarize_safe", lambda text, **kw: seen.append(text) or "ok")
    client.post("/diagnose", json={"symptom_text": f"   {SYMPTOM}   "})
    assert seen == [SYMPTOM]


def test_too_short_or_too_long_is_422_without_calling_ai_or_saving(monkeypatch, saved):
    def must_not_run(text):
        raise AssertionError("AI must not be called")

    monkeypatch.setattr(ai, "summarize_safe", must_not_run)
    for text in ["", "ngắn", "          x", "a" * 1001]:
        assert client.post("/diagnose", json={"symptom_text": text}).status_code == 422, text
    assert saved == []


@pytest.mark.parametrize(
    ("reason", "code"),
    [
        ("GEMINI_API_KEY is not set", "NO_KEY"),
        ("HTTP 429 after 3 attempts", "RATE_LIMITED"),
        ("timeout", "TIMEOUT"),
        ("HTTP 400 (not retried)", "UPSTREAM_ERROR"),
        ("HTTP 503 after 3 attempts", "UPSTREAM_ERROR"),
        ("network error: ConnectError", "UPSTREAM_ERROR"),
    ],
)
def test_ai_failure_is_a_friendly_503_and_saved_with_its_code(monkeypatch, saved, capsys, reason, code):
    def broken(text, **kw):
        raise ai.AIUnavailable(reason)

    monkeypatch.setattr(ai, "summarize_safe", broken)
    r = client.post("/diagnose", json={"symptom_text": SYMPTOM})
    assert r.status_code == 503
    assert r.json() == {
        "error_code": "AI_UNAVAILABLE",
        "message": "Tính năng chẩn đoán AI tạm thời không khả dụng, vui lòng thử lại sau ít phút.",
    }
    assert f"ai failed: {reason}" in capsys.readouterr().out  # the reason only in the logs
    assert saved[0]["status"] == "FAILED"
    assert saved[0]["error_code"] == code
    assert saved[0]["ai_suggestion"] is None


def test_missing_key_is_a_friendly_503_not_a_crash(monkeypatch, saved):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    r = client.post("/diagnose", json={"symptom_text": SYMPTOM})
    assert r.status_code == 503
    assert r.json()["error_code"] == "AI_UNAVAILABLE"
    assert saved[0]["error_code"] == "NO_KEY"


def test_answer_still_reaches_the_user_when_the_database_is_down(monkeypatch, capsys):
    def broken_connection(timeout=None):
        raise psycopg.OperationalError("connection refused")

    monkeypatch.setattr(db.pool, "connection", broken_connection)
    monkeypatch.setattr(ai, "summarize_safe", lambda text, **kw: "Má phanh mòn.")
    r = client.post("/diagnose", json={"symptom_text": SYMPTOM})
    assert r.status_code == 200
    assert "diagnosis not saved" in capsys.readouterr().out


def test_history_lists_saved_diagnoses(monkeypatch):
    row = {
        "id": 2, "created_at": datetime(2026, 10, 18, 13, 15, tzinfo=UTC), "symptom_text": SYMPTOM,
        "status": "FAILED", "ai_suggestion": None, "urgency_level": None, "error_code": "RATE_LIMITED", "model": "gemini-flash",
    }

    @contextmanager
    def connection(timeout=None):
        yield FakeConnection([], [row])

    monkeypatch.setattr(db.pool, "connection", connection)
    r = client.get("/api/diagnoses")
    assert r.status_code == 200
    assert r.json()[0]["error_code"] == "RATE_LIMITED"
    assert r.json()[0]["status"] == "FAILED"


def test_history_returns_error_out_when_database_is_down(monkeypatch):
    def broken_connection(timeout=None):
        raise psycopg.OperationalError("connection refused")

    monkeypatch.setattr(db.pool, "connection", broken_connection)
    r = client.get("/api/diagnoses")
    assert r.status_code == 503
    assert r.json()["error_code"] == "DB_UNAVAILABLE"


def test_ai_pages_load_without_database(monkeypatch):
    def broken_connection(timeout=None):
        raise AssertionError("pages are shells; data comes from the API")

    monkeypatch.setattr(db.pool, "connection", broken_connection)
    r = client.get("/chan-doan")
    assert r.status_code == 200
    assert 'id="symptom"' in r.text
    assert "/static/diagnose.js" in r.text
    r = client.get("/chan-doan/lich-su")
    assert r.status_code == 200
    assert "/static/ai_history.js" in r.text
    for path in ["/static/diagnose.js", "/static/ai_history.js"]:
        assert client.get(path).status_code == 200, path
