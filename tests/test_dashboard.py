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

VEHICLES = [
    {"id": 1, "name": "Vision đi làm", "vehicle_type": "MOTORBIKE", "license_plate": "59X1-123.45", "current_odometer": 12850},
    {"id": 2, "name": "Vios gia đình", "vehicle_type": "CAR", "license_plate": "51H-678.90", "current_odometer": 45200},
    {"id": 3, "name": "Air Blade", "vehicle_type": "MOTORBIKE", "license_plate": None, "current_odometer": 20300},
]

# rows of v_reminder_status as the home screen's vehicle cards read them
REMINDERS = [
    {"vehicle_id": 1, "service_type_name": "Thay lọc gió", "status": "OK", "days_left": 138, "km_left": 6950,
     "next_due_date": date(2027, 3, 10), "next_due_odometer": 19800, "base_date": date(2026, 3, 10),
     "base_odometer": 9800, "current_odometer": 12850, "interval_km": 10000},
    {"vehicle_id": 1, "service_type_name": "Thay nhớt máy (xe máy)", "status": "OVERDUE", "days_left": -3, "km_left": 1150,
     "next_due_date": date(2026, 10, 20), "next_due_odometer": 14000, "base_date": date(2026, 8, 20),
     "base_odometer": 12500, "current_odometer": 12850, "interval_km": 1500},
    {"vehicle_id": 2, "service_type_name": "Thay dầu động cơ (ô tô)", "status": "OK", "days_left": 102, "km_left": 4600,
     "next_due_date": date(2027, 2, 2), "next_due_odometer": 49800, "base_date": date(2026, 8, 2),
     "base_odometer": 44800, "current_odometer": 45200, "interval_km": 5000},
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
        if "date_trunc('year'" in self.query:
            return {"total": Decimal(3880000)}
        return {"total": Decimal(0)}

    def fetchall(self):
        if "FROM vehicles" in self.query:
            return VEHICLES
        if "v_reminder_status" in self.query:
            return ATTENTION if "status <> 'OK'" in self.query else REMINDERS
        return RECENT


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
    assert Decimal(body["cost_this_year"]) == 3880000


def test_each_vehicle_card_shows_its_most_urgent_reminder(monkeypatch):
    monkeypatch.setattr(db.pool, "connection", fake_connection)
    vision, vios, air_blade = client.get("/api/stats/dashboard").json()["vehicles"]
    # Vision has an OK and an overdue reminder: the overdue one wins, and its gauge is full
    assert vision["reminder"]["service_type_name"] == "Thay nhớt máy (xe máy)"
    assert vision["reminder"]["status"] == "OVERDUE"
    assert vision["reminder"]["progress"] == 1.0
    # Vios: 400 of 5000 km and 82 of 184 days used, so the larger share (time) counts
    assert vios["reminder"]["progress"] == round(82 / 184, 3)
    # Air Blade has no reminder: the card still shows, without a gauge
    assert air_blade["reminder"] is None
    assert air_blade["license_plate"] is None


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
    assert "Việc nên làm trước" in r.text
    assert "Xe của bạn" in r.text
    assert f"v{APP_VERSION}" in r.text


def test_upcoming_pages_exist():
    for path in ["/thong-ke", "/loai-dich-vu", "/them"]:
        r = client.get(path)
        assert r.status_code == 200, path
        assert "đang được xây dựng" in r.text


def test_static_files_are_served():
    for path in ["/static/style.css", "/static/app.js", "/static/dashboard.js", "/static/ai_history.js"]:
        assert client.get(path).status_code == 200, path


def test_health_routes_are_not_shadowed_by_pages():
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/docs").status_code == 200
