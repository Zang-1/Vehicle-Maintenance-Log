from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from psycopg.errors import UniqueViolation

from app.main import app
from app.schemas import today_vn
from tests.fakedb import Seq, use_fake_db

client = TestClient(app)

VEHICLE = {"id": 1, "is_archived": False}
RECORD = {
    "record_id": 10, "vehicle_id": 1, "vehicle_name": "Vision đi làm", "license_plate": "59X1-123.45",
    "service_date": date(2026, 10, 22), "odometer": 13000, "garage_name": "Honda Head", "note": None,
    "item_count": 2, "total_cost": Decimal(990000),
}
ITEMS = [
    {"id": 1, "service_type_id": 1, "service_type_name": "Thay nhớt máy (xe máy)", "description": "Nhớt Castrol",
     "quantity": Decimal("4.00"), "unit_price": Decimal(210000), "line_total": Decimal(840000)},
    {"id": 2, "service_type_id": 4, "service_type_name": "Thay lọc gió", "description": None,
     "quantity": Decimal("1.00"), "unit_price": Decimal(150000), "line_total": Decimal(150000)},
]
TYPES_OK = [{"id": 1, "is_active": True}, {"id": 4, "is_active": True}]

BODY = {
    "service_date": today_vn().isoformat(),
    "odometer": 13000,
    "garage_name": " Honda Head ",
    "note": "",
    "items": [
        {"service_type_id": 1, "description": "Nhớt Castrol", "quantity": 4, "unit_price": 210000},
        {"service_type_id": 4, "quantity": 1, "unit_price": 150000},
    ],
}


def saved_record_script(*extra):
    """What the database answers when a record is saved and read back."""
    return [
        ("is_archived FROM vehicles", VEHICLE),
        ("FROM service_types WHERE id = ANY", TYPES_OK),
        ("INSERT INTO maintenance_records", {"id": 10}),
        ("WHERE t.record_id", RECORD),
        ("WHERE i.record_id = %(id)s", ITEMS),
        *extra,
    ]


# ---------- create ----------


def test_create_record_saves_record_items_and_raises_the_odometer(monkeypatch):
    cursor = use_fake_db(monkeypatch, saved_record_script())
    r = client.post("/api/vehicles/1/records", json=BODY)
    assert r.status_code == 201
    body = r.json()
    assert body["record_id"] == 10
    assert body["total_cost"] == "990000"  # TC-06: 4 x 210.000 + 1 x 150.000
    assert [i["line_total"] for i in body["items"]] == ["840000", "150000"]

    inserted = cursor.calls_matching("INSERT INTO maintenance_records")[0]
    assert inserted["garage_name"] == "Honda Head" and inserted["note"] is None  # trimmed, "" is NULL
    items = cursor.calls_matching("INSERT INTO maintenance_items")[0]
    assert [i["service_type_id"] for i in items] == [1, 4] and all(i["record_id"] == 10 for i in items)
    assert items[0]["quantity"] == Decimal(4) and items[0]["unit_price"] == Decimal(210000)
    raised = cursor.calls_matching("UPDATE vehicles SET current_odometer")[0]
    assert raised == {"vehicle_id": 1, "odometer": 13000}  # TC-07; the SQL itself only ever raises (BR-02)
    assert "current_odometer < %(odometer)s" in next(sql for sql, _ in cursor.calls if "UPDATE vehicles" in sql)


def test_create_record_runs_its_writes_in_order(monkeypatch):
    cursor = use_fake_db(monkeypatch, saved_record_script())
    client.post("/api/vehicles/1/records", json=BODY)
    writes = [sql for sql, _ in cursor.calls if sql.startswith(("INSERT", "UPDATE"))]
    assert [w.split(" SET")[0].split(" (")[0] for w in writes] == [
        "INSERT INTO maintenance_records",
        "INSERT INTO maintenance_items",
        "UPDATE vehicles",
    ]


def test_create_record_rejects_bad_input_before_touching_the_database(monkeypatch):
    cursor = use_fake_db(monkeypatch, saved_record_script())
    item = {"service_type_id": 1, "quantity": 1, "unit_price": 1000}
    bad = [
        {**BODY, "items": []},  # TC-04, BR-04
        {**BODY, "service_date": (today_vn() + timedelta(days=1)).isoformat()},  # TC-05, BR-03
        {**BODY, "odometer": -1},
        {**BODY, "items": [{**item, "quantity": 0}]},
        {**BODY, "items": [{**item, "quantity": 0.123}]},
        {**BODY, "items": [{**item, "unit_price": -1}]},
        {**BODY, "items": [{**item, "unit_price": 1.5}]},
        {**BODY, "items": [{**item, "service_type_id": 0}]},
        {**BODY, "items": [{**item, "quantity": 999999.99, "unit_price": 999999999999}]},  # would overflow line_total
        {key: value for key, value in BODY.items() if key != "service_date"},
    ]
    for body in bad:
        assert client.post("/api/vehicles/1/records", json=body).status_code == 422, body
    assert cursor.calls == []


def test_a_date_is_in_the_future_by_the_calendar_of_vietnam(monkeypatch):
    # The server clock is UTC; app.schemas.today_vn() is the date a user in Vietnam sees (BR-03).
    monkeypatch.setattr("app.schemas.today_vn", lambda: date(2026, 10, 22))
    use_fake_db(monkeypatch, saved_record_script())
    assert client.post("/api/vehicles/1/records", json={**BODY, "service_date": "2026-10-22"}).status_code == 201
    assert client.post("/api/vehicles/1/records", json={**BODY, "service_date": "2026-10-23"}).status_code == 422


def test_create_record_for_unknown_vehicle_is_404(monkeypatch):
    use_fake_db(monkeypatch, [("is_archived FROM vehicles", None)])
    r = client.post("/api/vehicles/99/records", json=BODY)
    assert r.status_code == 404 and r.json()["error_code"] == "VEHICLE_NOT_FOUND"


def test_create_record_for_an_archived_vehicle_is_409(monkeypatch):
    cursor = use_fake_db(monkeypatch, [("is_archived FROM vehicles", {"id": 1, "is_archived": True})])
    r = client.post("/api/vehicles/1/records", json=BODY)
    assert r.status_code == 409 and r.json()["error_code"] == "VEHICLE_ARCHIVED"
    assert cursor.calls_matching("INSERT INTO maintenance_records") == []


def test_create_record_with_an_unknown_service_type_is_422(monkeypatch):
    cursor = use_fake_db(monkeypatch, [("is_archived FROM vehicles", VEHICLE), ("FROM service_types WHERE id = ANY", [{"id": 1, "is_active": True}])])
    r = client.post("/api/vehicles/1/records", json=BODY)  # asks for type 4 as well
    assert r.status_code == 422 and r.json()["error_code"] == "SERVICE_TYPE_NOT_FOUND"
    assert cursor.calls_matching("INSERT INTO maintenance_records") == []


def test_create_record_with_a_retired_service_type_is_422(monkeypatch):
    types = [{"id": 1, "is_active": True}, {"id": 4, "is_active": False}]  # BR-09: retired types leave the pick list
    use_fake_db(monkeypatch, [("is_archived FROM vehicles", VEHICLE), ("FROM service_types WHERE id = ANY", types)])
    r = client.post("/api/vehicles/1/records", json=BODY)
    assert r.status_code == 422 and r.json()["error_code"] == "SERVICE_TYPE_INACTIVE"


def test_create_duplicate_record_is_409(monkeypatch):
    use_fake_db(monkeypatch, [*saved_record_script()[:2], ("INSERT INTO maintenance_records", UniqueViolation())])
    r = client.post("/api/vehicles/1/records", json=BODY)  # same vehicle + date + odometer (BR-04)
    assert r.status_code == 409 and r.json()["error_code"] == "DUPLICATE_RECORD"


# ---------- read ----------


def test_history_lists_a_vehicles_records(monkeypatch):
    row = {**RECORD, "items_summary": "Thay lọc gió, Thay nhớt máy (xe máy)"}
    cursor = use_fake_db(monkeypatch, [("is_archived FROM vehicles", VEHICLE), ("FROM v_record_totals t WHERE", [row])])
    r = client.get("/api/vehicles/1/records?from_date=2026-01-01&to_date=2026-12-31")
    assert r.status_code == 200
    assert r.json()[0]["items_summary"].startswith("Thay lọc gió")
    assert cursor.calls_matching("FROM v_record_totals t")[0] == {"vehicle_id": 1, "from_date": date(2026, 1, 1), "to_date": date(2026, 12, 31)}


def test_history_without_dates_and_with_bad_dates(monkeypatch):
    cursor = use_fake_db(monkeypatch, [("is_archived FROM vehicles", VEHICLE)])
    assert client.get("/api/vehicles/1/records").status_code == 200
    assert cursor.calls_matching("FROM v_record_totals t")[0] == {"vehicle_id": 1, "from_date": None, "to_date": None}
    assert client.get("/api/vehicles/1/records?from_date=not-a-date").status_code == 422


def test_history_of_an_unknown_vehicle_is_404(monkeypatch):
    use_fake_db(monkeypatch, [("is_archived FROM vehicles", None)])
    assert client.get("/api/vehicles/99/records").status_code == 404


def test_read_one_record_with_its_items(monkeypatch):
    use_fake_db(monkeypatch, [("WHERE t.record_id", RECORD), ("WHERE i.record_id = %(id)s", ITEMS)])
    body = client.get("/api/records/10").json()
    assert body["vehicle_name"] == "Vision đi làm" and body["license_plate"] == "59X1-123.45"
    assert body["items"][0]["service_type_name"] == "Thay nhớt máy (xe máy)"


def test_read_unknown_record_is_404(monkeypatch):
    use_fake_db(monkeypatch, [("WHERE t.record_id", None)])
    r = client.get("/api/records/99")
    assert r.status_code == 404 and r.json()["error_code"] == "RECORD_NOT_FOUND"


# ---------- update, delete ----------


def test_update_record_replaces_items_and_raises_the_odometer(monkeypatch):
    cursor = use_fake_db(
        monkeypatch,
        [
            ("SELECT DISTINCT service_type_id", [{"service_type_id": 1}]),
            ("FROM service_types WHERE id = ANY", TYPES_OK),
            ("UPDATE maintenance_records", {"vehicle_id": 1}),
            ("WHERE t.record_id", RECORD),
            ("WHERE i.record_id = %(id)s", ITEMS),
        ],
    )
    r = client.put("/api/records/10", json=BODY)
    assert r.status_code == 200
    assert cursor.calls_matching("DELETE FROM maintenance_items") == [{"id": 10}]
    assert len(cursor.calls_matching("INSERT INTO maintenance_items")[0]) == 2
    assert cursor.calls_matching("UPDATE vehicles SET current_odometer")[0] == {"vehicle_id": 1, "odometer": 13000}


def test_update_record_may_keep_a_service_type_retired_since(monkeypatch):
    types = [{"id": 1, "is_active": False}, {"id": 4, "is_active": True}]
    use_fake_db(
        monkeypatch,
        [
            ("SELECT DISTINCT service_type_id", [{"service_type_id": 1}]),  # type 1 is already on this record
            ("FROM service_types WHERE id = ANY", types),
            ("UPDATE maintenance_records", {"vehicle_id": 1}),
            ("WHERE t.record_id", RECORD),
        ],
    )
    assert client.put("/api/records/10", json=BODY).status_code == 200


def test_update_unknown_record_is_404(monkeypatch):
    use_fake_db(monkeypatch, [("FROM service_types WHERE id = ANY", TYPES_OK), ("UPDATE maintenance_records", None)])
    assert client.put("/api/records/99", json=BODY).status_code == 404


def test_update_into_an_existing_date_and_odometer_is_409(monkeypatch):
    use_fake_db(monkeypatch, [("FROM service_types WHERE id = ANY", TYPES_OK), ("UPDATE maintenance_records", UniqueViolation())])
    assert client.put("/api/records/10", json=BODY).status_code == 409


def test_delete_record(monkeypatch):
    cursor = use_fake_db(monkeypatch, [("DELETE FROM maintenance_records", Seq({"id": 10}, None))])
    r = client.delete("/api/records/10")
    assert r.status_code == 204 and r.content == b""
    assert client.delete("/api/records/10").status_code == 404
    assert cursor.calls_matching("UPDATE vehicles") == []  # the odometer stays where it is (BR-02)


# ---------- CSV (FR-10) ----------


def csv_row(**changes):
    row = {
        "service_date": date(2026, 10, 22), "odometer": 13000, "garage_name": "Honda Head", "note": None,
        "service_type_name": "Thay lọc gió", "description": None, "quantity": Decimal("1.00"),
        "unit_price": Decimal(150000), "line_total": Decimal(150000),
    }
    return {**row, **changes}


def test_csv_export(monkeypatch):
    use_fake_db(monkeypatch, [("is_archived FROM vehicles", VEHICLE), ("FROM maintenance_records r", [csv_row(), csv_row(odometer=12500)])])
    r = client.get("/api/vehicles/1/records.csv")
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    assert 'filename="lich-su-xe-1.csv"' in r.headers["content-disposition"]
    text = r.content.decode("utf-8")
    assert text.startswith("﻿")  # BOM: Excel then reads the Vietnamese text correctly
    lines = text.lstrip("﻿").strip().splitlines()
    assert lines[0].startswith("Ngày,Số km,Nơi làm")
    assert lines[1].startswith("22/10/2026,13000,Honda Head")
    assert len(lines) == 3


def test_csv_does_not_run_formulas(monkeypatch):
    use_fake_db(monkeypatch, [("is_archived FROM vehicles", VEHICLE), ("FROM maintenance_records r", [csv_row(note="=HYPERLINK(1)", description="+cmd")])])
    text = client.get("/api/vehicles/1/records.csv").content.decode("utf-8")
    assert "'=HYPERLINK(1)" in text and "'+cmd" in text


def test_csv_of_an_unknown_vehicle_is_404(monkeypatch):
    use_fake_db(monkeypatch, [("is_archived FROM vehicles", None)])
    assert client.get("/api/vehicles/99/records.csv").status_code == 404


# ---------- pages ----------


def test_record_pages_render():
    add = client.get("/bao-duong/moi?xe=1&loai=2")
    assert add.status_code == 200 and 'data-record-id=""' in add.text and "Ghi lần bảo dưỡng" in add.text
    detail = client.get("/bao-duong/7")
    assert detail.status_code == 200 and 'data-record-id="7"' in detail.text
    edit = client.get("/bao-duong/7/sua")
    assert edit.status_code == 200 and 'data-record-id="7"' in edit.text and "Sửa lần bảo dưỡng" in edit.text


def test_record_page_ids_must_be_numbers():
    assert client.get("/bao-duong/abc").status_code == 404
    assert client.get("/bao-duong/abc/sua").status_code == 404


def test_record_page_scripts_are_served():
    for name in ["record_form.js", "record_detail.js"]:
        assert client.get(f"/static/{name}").status_code == 200, name
