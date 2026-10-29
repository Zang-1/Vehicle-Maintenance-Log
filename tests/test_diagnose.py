from fastapi.testclient import TestClient

from app import ai, db
from app.main import app

client = TestClient(app)

SYMPTOM = "Phanh trước kêu rít khi bóp mạnh, tay phanh hơi sâu"


def broken_connection(timeout=None):
    raise AssertionError("/diagnose must not need the database")


def test_diagnose_returns_the_ai_suggestion(monkeypatch):
    monkeypatch.setattr(db.pool, "connection", broken_connection)
    monkeypatch.setattr(ai, "summarize_safe", lambda text: "Má phanh mòn.\nMức khẩn cấp: MEDIUM")
    r = client.post("/diagnose", json={"symptom_text": SYMPTOM})
    assert r.status_code == 200
    assert r.json() == {"suggestion": "Má phanh mòn.\nMức khẩn cấp: MEDIUM"}


def test_symptom_is_trimmed_before_the_ai_call(monkeypatch):
    seen = []
    monkeypatch.setattr(ai, "summarize_safe", lambda text: seen.append(text) or "ok")
    client.post("/diagnose", json={"symptom_text": f"   {SYMPTOM}   "})
    assert seen == [SYMPTOM]


def test_too_short_or_too_long_is_422_without_calling_ai(monkeypatch):
    def must_not_run(text):
        raise AssertionError("AI must not be called")

    monkeypatch.setattr(ai, "summarize_safe", must_not_run)
    for text in ["", "ngắn", "          x", "a" * 1001]:
        assert client.post("/diagnose", json={"symptom_text": text}).status_code == 422, text


def test_ai_failure_is_a_friendly_503(monkeypatch, capsys):
    def broken(text):
        raise ai.AIUnavailable("HTTP 400 (not retried)")

    monkeypatch.setattr(ai, "summarize_safe", broken)
    r = client.post("/diagnose", json={"symptom_text": SYMPTOM})
    assert r.status_code == 503
    assert r.json() == {
        "error_code": "AI_UNAVAILABLE",
        "message": "Tính năng chẩn đoán AI tạm thời không khả dụng, vui lòng thử lại sau ít phút.",
    }
    assert "ai failed: HTTP 400 (not retried)" in capsys.readouterr().out  # the reason only in the logs


def test_missing_key_is_a_friendly_503_not_a_crash(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    r = client.post("/diagnose", json={"symptom_text": SYMPTOM})
    assert r.status_code == 503
    assert r.json()["error_code"] == "AI_UNAVAILABLE"


def test_diagnose_page_loads_without_database(monkeypatch):
    monkeypatch.setattr(db.pool, "connection", broken_connection)
    r = client.get("/chan-doan")
    assert r.status_code == 200
    assert 'id="symptom"' in r.text
    assert "/static/diagnose.js" in r.text
    assert client.get("/static/diagnose.js").status_code == 200
