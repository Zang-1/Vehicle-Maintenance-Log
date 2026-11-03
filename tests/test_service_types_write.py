from fastapi.testclient import TestClient
from psycopg.errors import UniqueViolation

from app.main import app
from tests.fakedb import use_fake_db

client = TestClient(app)

ROW = {
    "id": 7, "name": "Thay nhớt", "description": None, "applies_to": "ALL",
    "default_interval_km": 2000, "default_interval_months": 3, "is_active": True, "is_builtin": False,
}
BODY = {"name": "Thay nhớt", "applies_to": "ALL", "default_interval_km": 2000, "default_interval_months": 3}


def test_create_service_type(monkeypatch):
    cursor = use_fake_db(monkeypatch, [
        ("INSERT INTO service_types", {"id": 7}),
        ("FROM service_types WHERE id", ROW),
    ])
    response = client.post("/api/service-types", json=BODY)
    assert response.status_code == 201
    assert response.json()["name"] == "Thay nhớt"
    assert cursor.calls_matching("INSERT INTO service_types")[0]["applies_to"] == "ALL"


def test_create_duplicate_name_returns_409(monkeypatch):
    use_fake_db(monkeypatch, [("INSERT INTO service_types", UniqueViolation())])
    response = client.post("/api/service-types", json=BODY)
    assert response.status_code == 409
    assert response.json()["error_code"] == "DUPLICATE_SERVICE_TYPE"


def test_create_rejects_bad_input(monkeypatch):
    use_fake_db(monkeypatch, [])
    assert client.post("/api/service-types", json={**BODY, "name": "   "}).status_code == 422
    assert client.post("/api/service-types", json={**BODY, "default_interval_km": 0}).status_code == 422
    assert client.post("/api/service-types", json={**BODY, "applies_to": "BOAT"}).status_code == 422


def test_update_missing_returns_404(monkeypatch):
    use_fake_db(monkeypatch, [("FROM service_types WHERE id", None)])
    assert client.put("/api/service-types/99", json=BODY).status_code == 404


def test_retire_service_type(monkeypatch):
    cursor = use_fake_db(monkeypatch, [
        ("UPDATE service_types SET is_active", None),
        ("FROM service_types WHERE id", {**ROW, "is_active": False}),
    ])
    response = client.patch("/api/service-types/7/active", json={"active": False})
    assert response.status_code == 200
    assert response.json()["is_active"] is False
    assert cursor.calls_matching("SET is_active")[0] == {"id": 7, "active": False, "uid": 1}


def test_service_types_page_is_real():
    response = client.get("/loai-dich-vu")
    assert response.status_code == 200
    assert "Loại việc bảo dưỡng" in response.text
    assert "đang được xây dựng" not in response.text

def test_delete_unused_service_type(monkeypatch):
    cursor = use_fake_db(monkeypatch, [
        ("DELETE FROM service_types", None),
        ("FROM service_types WHERE id", {**ROW, "used_count": 0}),
    ])
    response = client.delete("/api/service-types/7")
    assert response.status_code == 204
    assert cursor.calls_matching("DELETE FROM service_types")[0] == {"id": 7, "uid": 1}


def test_delete_used_service_type_returns_409(monkeypatch):
    cursor = use_fake_db(monkeypatch, [
        ("DELETE FROM service_types", None),
        ("FROM service_types WHERE id", {**ROW, "used_count": 3}),
    ])
    response = client.delete("/api/service-types/7")
    assert response.status_code == 409
    assert response.json()["error_code"] == "SERVICE_TYPE_IN_USE"
    assert not cursor.calls_matching("DELETE FROM service_types")


def test_delete_missing_service_type_returns_404(monkeypatch):
    use_fake_db(monkeypatch, [("FROM service_types WHERE id", None)])
    assert client.delete("/api/service-types/99").status_code == 404