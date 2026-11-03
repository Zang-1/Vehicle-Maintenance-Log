from datetime import date, datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from psycopg.errors import UniqueViolation

from app.main import app
from tests.fakedb import Seq, use_fake_db

client = TestClient(app)

ROW = {
    "id": 1, "name": "Vision đi làm", "vehicle_type": "MOTORBIKE", "brand": "Honda", "model": "Vision",
    "manufacture_year": 2022, "license_plate": "59X1-123.45", "current_odometer": 12850,
    "purchase_date": date(2022, 3, 1), "is_archived": False, "created_at": datetime(2026, 10, 1, 8, 0),
    "record_count": 3, "last_service_date": date(2026, 8, 20), "total_cost": Decimal(705000),
    "overdue_count": 1, "due_soon_count": 0,
}

NEW = {"name": "Wave", "vehicle_type": "MOTORBIKE", "current_odometer": 1000}


def test_list_defaults_to_active_vehicles(monkeypatch):
    cursor = use_fake_db(monkeypatch, [("FROM vehicles v", [ROW])])
    r = client.get("/api/vehicles")
    assert r.status_code == 200
    body = r.json()
    assert body[0]["name"] == "Vision đi làm"
    assert body[0]["total_cost"] == "705000"  # Decimal travels as a string
    assert body[0]["overdue_count"] == 1
    assert cursor.calls[0][1] == {"archived": False, "uid": 1}  # FR-25: only the signed-in user's vehicles


def test_list_filters_archived_and_all(monkeypatch):
    cursor = use_fake_db(monkeypatch, [("FROM vehicles v", [])])
    assert client.get("/api/vehicles?archived=archived").json() == []
    assert client.get("/api/vehicles?archived=all").json() == []
    assert [call[1] for call in cursor.calls] == [{"archived": True, "uid": 1}, {"archived": None, "uid": 1}]


def test_list_rejects_an_unknown_filter(monkeypatch):
    use_fake_db(monkeypatch, [])
    assert client.get("/api/vehicles?archived=zzz").status_code == 422


def test_create_vehicle_cleans_the_input(monkeypatch):
    cursor = use_fake_db(monkeypatch, [("INSERT INTO vehicles", {"id": 1}), ("WHERE v.id", ROW)])
    body = {**NEW, "name": "  Wave ", "license_plate": " 59x1-123.45 ", "brand": "  ", "model": ""}
    r = client.post("/api/vehicles", json=body)
    assert r.status_code == 201
    sent = cursor.calls_matching("INSERT INTO vehicles")[0]
    assert sent["name"] == "Wave"
    assert sent["license_plate"] == "59X1-123.45"  # BR-01: the plate is stored in capitals
    assert sent["brand"] is None and sent["model"] is None  # an empty box is NULL, not ""
    assert sent["vehicle_type"] == "MOTORBIKE"


def test_create_vehicle_needs_only_name_and_type(monkeypatch):
    cursor = use_fake_db(monkeypatch, [("INSERT INTO vehicles", {"id": 1}), ("WHERE v.id", ROW)])
    r = client.post("/api/vehicles", json={"name": "Xe cũ", "vehicle_type": "OTHER"})
    assert r.status_code == 201
    assert cursor.calls_matching("INSERT INTO vehicles")[0]["current_odometer"] == 0


def test_create_vehicle_with_a_taken_plate_is_409(monkeypatch):
    use_fake_db(monkeypatch, [("INSERT INTO vehicles", UniqueViolation())])  # TC-01
    r = client.post("/api/vehicles", json={**NEW, "license_plate": "59X1-123.45"})
    assert r.status_code == 409
    assert r.json()["error_code"] == "DUPLICATE_PLATE"


def test_create_vehicle_validation_is_422_and_touches_nothing(monkeypatch):
    cursor = use_fake_db(monkeypatch, [])
    bad = [
        {**NEW, "name": "   "},
        {**NEW, "vehicle_type": "BOAT"},
        {**NEW, "manufacture_year": 1900},
        {**NEW, "manufacture_year": 2101},
        {**NEW, "current_odometer": -1},
        {**NEW, "purchase_date": "2999-01-01"},
        {"vehicle_type": "CAR"},
    ]
    for body in bad:
        assert client.post("/api/vehicles", json=body).status_code == 422, body
    assert cursor.calls == []


def test_read_vehicle_and_404(monkeypatch):
    use_fake_db(monkeypatch, [("WHERE v.id", Seq(ROW, None))])
    assert client.get("/api/vehicles/1").json()["id"] == 1
    r = client.get("/api/vehicles/99")
    assert r.status_code == 404
    assert r.json()["error_code"] == "VEHICLE_NOT_FOUND"


def test_vehicle_id_must_be_a_number(monkeypatch):
    use_fake_db(monkeypatch, [])
    assert client.get("/api/vehicles/abc").status_code == 422


def test_update_cannot_lower_the_odometer(monkeypatch):
    cursor = use_fake_db(monkeypatch, [("FOR UPDATE", {"current_odometer": 12850})])
    r = client.put("/api/vehicles/1", json={**NEW, "current_odometer": 12000})  # TC-02
    assert r.status_code == 422
    assert r.json()["error_code"] == "ODOMETER_DECREASE"
    assert "12.850" in r.json()["message"]
    assert cursor.calls_matching("UPDATE vehicles") == []


def test_update_with_a_higher_odometer(monkeypatch):
    cursor = use_fake_db(monkeypatch, [("FOR UPDATE", {"current_odometer": 12850}), ("WHERE v.id", ROW)])
    r = client.put("/api/vehicles/1", json={**NEW, "current_odometer": 13000})
    assert r.status_code == 200
    assert cursor.calls_matching("UPDATE vehicles")[0]["current_odometer"] == 13000


def test_update_unknown_vehicle_is_404(monkeypatch):
    use_fake_db(monkeypatch, [("FOR UPDATE", None)])
    assert client.put("/api/vehicles/99", json=NEW).status_code == 404


def test_update_to_a_taken_plate_is_409(monkeypatch):
    use_fake_db(monkeypatch, [("FOR UPDATE", {"current_odometer": 0}), ("UPDATE vehicles", UniqueViolation())])
    r = client.put("/api/vehicles/1", json={**NEW, "license_plate": "51H-678.90"})
    assert r.status_code == 409


def test_archive_and_restore(monkeypatch):
    cursor = use_fake_db(monkeypatch, [("WHERE v.id", ROW)])
    assert client.patch("/api/vehicles/1/archive").status_code == 200
    assert client.patch("/api/vehicles/1/archive", json={"archived": False}).status_code == 200
    assert [p["archived"] for p in cursor.calls_matching("SET is_archived")] == [True, False]


def test_archive_unknown_vehicle_is_404(monkeypatch):
    use_fake_db(monkeypatch, [("WHERE v.id", None)])
    assert client.patch("/api/vehicles/99/archive").status_code == 404


def test_delete_vehicle_with_history_is_refused(monkeypatch):
    cursor = use_fake_db(monkeypatch, [("WHERE v.id", ROW), ("count(*) AS n", {"n": 3})])
    r = client.delete("/api/vehicles/1")  # TC-03
    assert r.status_code == 409
    assert r.json()["error_code"] == "HAS_HISTORY"
    assert cursor.calls_matching("DELETE FROM vehicles") == []


def test_delete_vehicle_without_history(monkeypatch):
    cursor = use_fake_db(monkeypatch, [("WHERE v.id", ROW), ("count(*) AS n", {"n": 0})])
    r = client.delete("/api/vehicles/1")
    assert r.status_code == 204
    assert r.content == b""
    assert cursor.calls_matching("DELETE FROM vehicles") == [{"id": 1}]


def test_delete_unknown_vehicle_is_404(monkeypatch):
    use_fake_db(monkeypatch, [("WHERE v.id", None)])
    assert client.delete("/api/vehicles/99").status_code == 404


def test_vehicle_pages_render():
    assert "Xe của tôi" in client.get("/xe").text
    add = client.get("/xe/moi")
    assert add.status_code == 200 and 'data-vehicle-id=""' in add.text
    detail = client.get("/xe/5")
    assert detail.status_code == 200 and 'data-vehicle-id="5"' in detail.text
    edit = client.get("/xe/5/sua")
    assert edit.status_code == 200 and 'data-vehicle-id="5"' in edit.text and "Sửa thông tin xe" in edit.text


def test_vehicle_page_ids_must_be_numbers():
    assert client.get("/xe/abc").status_code == 404
    assert client.get("/xe/abc/sua").status_code == 404


def test_vehicle_page_scripts_are_served():
    for name in ["form_utils.js", "vehicles.js", "vehicle_form.js", "vehicle_detail.js"]:
        assert client.get(f"/static/{name}").status_code == 200, name
