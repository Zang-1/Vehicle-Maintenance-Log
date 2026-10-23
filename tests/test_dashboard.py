from contextlib import contextmanager
from datetime import date
from decimal import Decimal

import psycopg
from fastapi.testclient import TestClient

from app import db
from app.main import APP_VERSION, app

client = TestClient(app)

ATTENTION = [
    {
        "reminder_id": 1, "vehicle_id": 1, "vehicle_name": "Vision đi làm",
        "service_type_id": 1, "service_type_name": "Thay nhớt máy (xe máy)",
        "interval_km": 1500, "interval_months": 2,
        "base_date": date(2026, 8, 20), "base_odometer": 12500,
        "next_due_date": date(2026, 10, 20), "next_due_odometer": 14000,
        "days_left": -2, "km_left": 1150, "is_active": True, "status": "OVERDUE",
    },
]

RECENT = [
    {
        "record_id": 3, "vehicle_id": 1, "vehicle_name": "Vision đi làm",
        "service_date": date(2026, 8, 20), "odometer": 12500, "garage_name": "Honda Head Phát Tiến",
        "item_count": 2, "total_cost": Decimal(315000), "items_summary": "Bảo dưỡng phanh, Thay nhớt máy (xe máy)",
    },
]


class FakeCursor:
    """Answers each dashboard query by recognising its SQL."""

    def __init__(self):
        self.query = ""

    def execute(self, query):
        self.query = query
        return self

    def fetchone(self):
        if "count(*) AS n" in self.query:
            return {"n": 3}
        return {"total": Decimal(0)}

    def fetchall(self):
        return ATTENTION if "v_reminder_status" in self.query else RECENT


class FakeConnection:
    def cursor(self, row_factory=None):
        return FakeCursor()


@contextmanager
def fake_connection(timeout=None):
    yield FakeConnection()


def broken_connection(timeout=None):
    raise psycopg.OperationalError("connection refused")


def test_dashboard_api(monkeypatch):
    monkeypatch.setattr(db.pool, "connection", fake_connection)
    r = client.get("/api/stats/dashboard")
    assert r.status_code == 200
    body = r.json()
    assert body["vehicle_count"] == 3
    assert Decimal(body["cost_this_month"]) == 0
    assert body["attention_reminders"][0]["status"] == "OVERDUE"
    assert body["attention_reminders"][0]["days_left"] == -2
    assert body["recent_records"][0]["vehicle_name"] == "Vision đi làm"
    assert Decimal(body["recent_records"][0]["total_cost"]) == 315000


def test_dashboard_api_returns_error_out_when_database_is_down(monkeypatch):
    monkeypatch.setattr(db.pool, "connection", broken_connection)
    r = client.get("/api/stats/dashboard")
    assert r.status_code == 503
    assert r.json()["error_code"] == "DB_UNAVAILABLE"


def test_dashboard_page_needs_no_database(monkeypatch):
    monkeypatch.setattr(db.pool, "connection", broken_connection)  # the page is a shell; data comes from the API
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "Nhắc lịch cần chú ý" in r.text
    assert f"v{APP_VERSION}" in r.text


def test_upcoming_pages_exist():
    for path in ["/xe", "/loai-dich-vu", "/thong-ke", "/chan-doan"]:
        r = client.get(path)
        assert r.status_code == 200, path
        assert "đang được xây dựng" in r.text


def test_static_files_are_served():
    for path in ["/static/style.css", "/static/app.js", "/static/dashboard.js"]:
        assert client.get(path).status_code == 200, path


def test_health_routes_are_not_shadowed_by_pages():
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/docs").status_code == 200
