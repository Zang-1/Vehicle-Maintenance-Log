from fastapi.testclient import TestClient

from app.main import app
from tests.fakedb import use_fake_db

client = TestClient(app)

TYPE = {
    "id": 4, "name": "Thay lọc gió", "description": "Vệ sinh hoặc thay lọc gió", "applies_to": "ALL",
    "default_interval_km": 10000, "default_interval_months": 12, "is_active": True,
}


def test_list_service_types(monkeypatch):
    cursor = use_fake_db(monkeypatch, [("FROM service_types", [TYPE])])
    r = client.get("/api/service-types")
    assert r.status_code == 200
    assert r.json()[0]["name"] == "Thay lọc gió"
    assert cursor.calls[0][1] == {"active": None, "vehicle_type": None}


def test_list_only_active_types_for_a_vehicle_type(monkeypatch):
    cursor = use_fake_db(monkeypatch, [("FROM service_types", [TYPE])])
    assert client.get("/api/service-types?active=true&vehicle_type=MOTORBIKE").status_code == 200
    assert cursor.calls[0][1] == {"active": True, "vehicle_type": "MOTORBIKE"}


def test_list_rejects_an_unknown_vehicle_type(monkeypatch):
    use_fake_db(monkeypatch, [])
    assert client.get("/api/service-types?vehicle_type=BOAT").status_code == 422
