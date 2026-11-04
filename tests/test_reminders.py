from datetime import date, timedelta

from fastapi.testclient import TestClient
from psycopg.errors import UniqueViolation

from app.main import app
from app.schemas import today_vn
from tests.fakedb import use_fake_db

client = TestClient(app)

VEHICLE = {"id": 1, "is_archived": False, "current_odometer": 12850}
TYPE_OK = {"id": 6, "is_active": True}


def reminder(**changes):
    """A row of the reminder read-back query (v_reminder_status + reminders)."""
    row = {
        "reminder_id": 20, "vehicle_id": 1, "vehicle_name": "Vision đi làm", "service_type_id": 6,
        "service_type_name": "Bảo dưỡng phanh", "interval_km": 4000, "interval_months": 6,
        "base_date": date(2026, 8, 20), "base_odometer": 12500, "next_due_date": date(2027, 2, 20),
        "next_due_odometer": 16500, "current_odometer": 12850, "days_left": 108, "km_left": 3650,
        "is_active": True, "status": "OK", "notify_before_days": 7, "notify_before_km": 300,
        "start_date": date(2026, 8, 20), "start_odometer": 12500,
    }
    return {**row, **changes}


BODY = {"service_type_id": 6, "interval_km": 4000, "interval_months": 6}


def saved_reminder_script(*extra):
    """What the database answers when a reminder is created and read back."""
    return [
        *extra,
        ("is_archived, current_odometer FROM vehicles", VEHICLE),
        ("FROM service_types WHERE id = %(id)s", TYPE_OK),
        ("INSERT INTO reminders", {"id": 20}),
        ("WHERE s.reminder_id", reminder()),
    ]


# ---------- list and read ----------


def test_list_reminders_reads_the_view_for_the_users_vehicle(monkeypatch):
    rows = [
        reminder(reminder_id=2, service_type_id=1, status="OVERDUE", days_left=-15, km_left=1150),
        reminder(),
    ]
    cursor = use_fake_db(monkeypatch, [("is_archived, current_odometer FROM vehicles", VEHICLE), ("WHERE s.vehicle_id", rows)])
    r = client.get("/api/vehicles/1/reminders")
    assert r.status_code == 200
    body = r.json()
    assert [x["reminder_id"] for x in body] == [2, 20]
    assert body[0]["progress"] == 1.0  # overdue is a full bar
    assert 0 < body[1]["progress"] < 1
    assert body[1]["notify_before_km"] == 300 and body[1]["start_odometer"] == 12500
    assert cursor.calls_matching("WHERE s.vehicle_id")[0] == {"vehicle_id": 1, "uid": 1}
    sql = next(sql for sql, _ in cursor.calls if "WHERE s.vehicle_id" in sql)
    assert "v.user_id = %(uid)s" in sql and "ORDER BY s.is_active DESC" in sql


def test_list_reminders_of_a_vehicle_that_is_not_the_users_is_404(monkeypatch):
    cursor = use_fake_db(monkeypatch, [])
    r = client.get("/api/vehicles/2/reminders")
    assert r.status_code == 404 and r.json()["error_code"] == "VEHICLE_NOT_FOUND"
    assert cursor.calls_matching("FROM vehicles WHERE id")[0] == {"id": 2, "uid": 1}
    assert cursor.calls_matching("FROM v_reminder_status") == []


def test_read_one_reminder(monkeypatch):
    cursor = use_fake_db(monkeypatch, [("WHERE s.reminder_id", reminder())])
    r = client.get("/api/reminders/20")
    assert r.status_code == 200 and r.json()["service_type_name"] == "Bảo dưỡng phanh"
    assert cursor.calls_matching("WHERE s.reminder_id")[0] == {"id": 20, "uid": 1}


def test_read_a_reminder_that_is_not_the_users_is_404(monkeypatch):
    use_fake_db(monkeypatch, [])
    r = client.get("/api/reminders/20")
    assert r.status_code == 404 and r.json()["error_code"] == "REMINDER_NOT_FOUND"


# ---------- create ----------


def test_create_reminder_starts_from_the_last_record_of_that_service(monkeypatch):
    last = ("FROM maintenance_records r JOIN maintenance_items", {"service_date": date(2026, 8, 20), "odometer": 12500})
    cursor = use_fake_db(monkeypatch, saved_reminder_script(last))
    r = client.post("/api/vehicles/1/reminders", json=BODY)
    assert r.status_code == 201 and r.json()["reminder_id"] == 20
    assert cursor.calls_matching("FROM maintenance_records r")[0] == {"vehicle_id": 1, "service_type_id": 6}
    inserted = cursor.calls_matching("INSERT INTO reminders")[0]
    assert inserted == {
        "vehicle_id": 1, "service_type_id": 6, "interval_km": 4000, "interval_months": 6,
        "notify_before_days": 7, "notify_before_km": 300,  # BR-06 defaults
        "start_date": date(2026, 8, 20), "start_odometer": 12500,  # BR-07
    }


def test_create_reminder_without_a_record_starts_today_at_the_vehicle_odometer(monkeypatch):
    monkeypatch.setattr("app.routers.reminders.today_vn", lambda: date(2026, 11, 4))
    cursor = use_fake_db(monkeypatch, saved_reminder_script())
    assert client.post("/api/vehicles/1/reminders", json=BODY).status_code == 201
    inserted = cursor.calls_matching("INSERT INTO reminders")[0]
    assert inserted["start_date"] == date(2026, 11, 4) and inserted["start_odometer"] == 12850


def test_create_reminder_keeps_a_start_mark_that_is_given(monkeypatch):
    cursor = use_fake_db(monkeypatch, saved_reminder_script())
    body = {**BODY, "start_date": "2026-01-15", "start_odometer": 9000, "notify_before_days": 0, "notify_before_km": 0}
    assert client.post("/api/vehicles/1/reminders", json=body).status_code == 201
    assert cursor.calls_matching("FROM maintenance_records r") == []
    inserted = cursor.calls_matching("INSERT INTO reminders")[0]
    assert inserted["start_date"] == date(2026, 1, 15) and inserted["start_odometer"] == 9000
    assert inserted["notify_before_days"] == 0 and inserted["notify_before_km"] == 0


def test_create_reminder_rejects_bad_input_before_touching_the_database(monkeypatch):
    cursor = use_fake_db(monkeypatch, saved_reminder_script())
    bad = [
        {"service_type_id": 6},  # BR-06: no interval
        {"service_type_id": 6, "interval_km": None, "interval_months": None},
        {**BODY, "interval_km": 0},
        {**BODY, "interval_months": 0},
        {**BODY, "interval_months": 241},
        {**BODY, "notify_before_days": -1},
        {**BODY, "notify_before_km": -1},
        {**BODY, "start_odometer": -1},
        {**BODY, "start_date": (today_vn() + timedelta(days=1)).isoformat()},
        {**BODY, "service_type_id": 0},
        {"interval_km": 4000},
    ]
    for body in bad:
        assert client.post("/api/vehicles/1/reminders", json=body).status_code == 422, body
    assert cursor.calls == []


def test_create_reminder_on_a_vehicle_that_is_not_the_users_is_404(monkeypatch):
    cursor = use_fake_db(monkeypatch, [])
    r = client.post("/api/vehicles/2/reminders", json=BODY)
    assert r.status_code == 404 and r.json()["error_code"] == "VEHICLE_NOT_FOUND"
    assert cursor.calls_matching("INSERT INTO reminders") == []


def test_create_reminder_on_an_archived_vehicle_is_409(monkeypatch):
    cursor = use_fake_db(monkeypatch, saved_reminder_script(("is_archived, current_odometer FROM vehicles", {**VEHICLE, "is_archived": True})))
    r = client.post("/api/vehicles/1/reminders", json=BODY)
    assert r.status_code == 409 and r.json()["error_code"] == "VEHICLE_ARCHIVED"
    assert cursor.calls_matching("INSERT INTO reminders") == []


def test_create_reminder_needs_a_known_active_service_type(monkeypatch):
    cursor = use_fake_db(monkeypatch, saved_reminder_script(("FROM service_types WHERE id = %(id)s", [])))
    r = client.post("/api/vehicles/1/reminders", json=BODY)
    assert r.status_code == 422 and r.json()["error_code"] == "SERVICE_TYPE_NOT_FOUND"
    sql = next(sql for sql, _ in cursor.calls if "FROM service_types" in sql)
    assert "user_id IS NULL OR user_id = %(uid)s" in sql  # a default type or one of the user's own

    use_fake_db(monkeypatch, saved_reminder_script(("FROM service_types WHERE id = %(id)s", {"id": 6, "is_active": False})))
    r = client.post("/api/vehicles/1/reminders", json=BODY)
    assert r.status_code == 422 and r.json()["error_code"] == "SERVICE_TYPE_INACTIVE"


def test_create_a_second_reminder_for_the_same_service_is_409(monkeypatch):
    use_fake_db(monkeypatch, saved_reminder_script(("INSERT INTO reminders", UniqueViolation())))
    r = client.post("/api/vehicles/1/reminders", json=BODY)
    assert r.status_code == 409 and r.json()["error_code"] == "DUPLICATE_REMINDER"  # BR-06


# ---------- update ----------


def test_update_reminder_keeps_the_start_mark_when_it_is_left_out(monkeypatch):
    cursor = use_fake_db(monkeypatch, [("FOR UPDATE OF rm", {"id": 20, "service_type_id": 6}), ("WHERE s.reminder_id", reminder())])
    body = {"service_type_id": 6, "interval_km": 3000, "notify_before_days": 10}
    r = client.put("/api/reminders/20", json=body)
    assert r.status_code == 200
    assert cursor.calls_matching("FOR UPDATE OF rm")[0] == {"id": 20, "uid": 1}
    updated = cursor.calls_matching("UPDATE reminders")[0]
    assert updated == {
        "id": 20, "interval_km": 3000, "interval_months": None, "notify_before_days": 10, "notify_before_km": 300,
        "start_date": None, "start_odometer": None,
    }
    sql = next(sql for sql, _ in cursor.calls if sql.startswith("UPDATE reminders"))
    assert "coalesce(%(start_date)s::date, start_date)" in sql


def test_update_reminder_cannot_change_the_service_type(monkeypatch):
    cursor = use_fake_db(monkeypatch, [("FOR UPDATE OF rm", {"id": 20, "service_type_id": 6})])
    r = client.put("/api/reminders/20", json={**BODY, "service_type_id": 5})
    assert r.status_code == 422 and r.json()["error_code"] == "SERVICE_TYPE_LOCKED"
    assert cursor.calls_matching("UPDATE reminders") == []


def test_update_a_reminder_that_is_not_the_users_is_404(monkeypatch):
    cursor = use_fake_db(monkeypatch, [])
    assert client.put("/api/reminders/20", json=BODY).status_code == 404
    assert cursor.calls_matching("UPDATE reminders") == []


# ---------- pause, resume, delete ----------


def test_pause_and_resume_a_reminder(monkeypatch):
    cursor = use_fake_db(monkeypatch, [("SET is_active", {"id": 20}), ("WHERE s.reminder_id", reminder(is_active=False))])
    r = client.patch("/api/reminders/20/active", json={"active": False})
    assert r.status_code == 200 and r.json()["is_active"] is False
    assert cursor.calls_matching("SET is_active")[0] == {"id": 20, "active": False, "uid": 1}
    sql = next(sql for sql, _ in cursor.calls if "SET is_active" in sql)
    assert "SELECT id FROM vehicles WHERE user_id = %(uid)s" in sql


def test_pause_a_reminder_that_is_not_the_users_is_404(monkeypatch):
    use_fake_db(monkeypatch, [])
    r = client.patch("/api/reminders/20/active", json={"active": False})
    assert r.status_code == 404 and r.json()["error_code"] == "REMINDER_NOT_FOUND"


def test_delete_reminder(monkeypatch):
    cursor = use_fake_db(monkeypatch, [("DELETE FROM reminders", {"id": 20})])
    r = client.delete("/api/reminders/20")
    assert r.status_code == 204 and r.content == b""
    assert cursor.calls_matching("DELETE FROM reminders")[0] == {"id": 20, "uid": 1}


def test_delete_a_reminder_that_is_not_the_users_is_404(monkeypatch):
    use_fake_db(monkeypatch, [])
    r = client.delete("/api/reminders/20")
    assert r.status_code == 404 and r.json()["error_code"] == "REMINDER_NOT_FOUND"
