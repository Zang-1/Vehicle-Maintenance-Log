"""Maintenance reminders (M5, FR-13, FR-14).

The due date, the due odometer and the status are never stored: v_reminder_status computes them from the
reminder's start mark and the latest record of the same service type (BR-07, BR-08). This router only keeps
the reminder itself.

BR-06 one reminder per vehicle + service type (UNIQUE, answered with 409) and at least one interval
(ReminderIn). Every route reaches a reminder through its vehicle, so another user's reminder is "not found".
"""

from fastapi import APIRouter, Response
from psycopg.errors import UniqueViolation
from psycopg.rows import dict_row

from app import db
from app.auth import CurrentUser
from app.errors import ApiError
from app.routers.stats import interval_used
from app.schemas import ActiveIn, ErrorOut, ReminderDetailOut, ReminderIn, today_vn

router = APIRouter(prefix="/api", tags=["reminders"])

SELECT_SQL = """
SELECT s.reminder_id, s.vehicle_id, s.vehicle_name, s.service_type_id, s.service_type_name,
       s.interval_km, s.interval_months, s.base_date, s.base_odometer, s.next_due_date, s.next_due_odometer,
       s.current_odometer, s.days_left, s.km_left, s.is_active, s.status,
       rm.notify_before_days, rm.notify_before_km, rm.start_date, rm.start_odometer
FROM v_reminder_status s
JOIN reminders rm ON rm.id = s.reminder_id
JOIN vehicles v ON v.id = s.vehicle_id
"""

# active first, then the most urgent
LIST_SQL = SELECT_SQL + """
WHERE s.vehicle_id = %(vehicle_id)s AND v.user_id = %(uid)s
ORDER BY s.is_active DESC,
         CASE s.status WHEN 'OVERDUE' THEN 0 WHEN 'DUE_SOON' THEN 1 ELSE 2 END,
         s.days_left NULLS LAST, s.km_left NULLS LAST, s.reminder_id
"""

ONE_SQL = SELECT_SQL + " WHERE s.reminder_id = %(id)s AND v.user_id = %(uid)s"

VEHICLE_SQL = "SELECT id, is_archived, current_odometer FROM vehicles WHERE id = %(id)s AND user_id = %(uid)s"

# a default type (user_id NULL) or one of the user's own
TYPE_SQL = "SELECT id, is_active FROM service_types WHERE id = %(id)s AND (user_id IS NULL OR user_id = %(uid)s)"

LAST_RECORD_SQL = """
SELECT r.service_date, r.odometer
FROM maintenance_records r
JOIN maintenance_items i ON i.record_id = r.id
WHERE r.vehicle_id = %(vehicle_id)s AND i.service_type_id = %(service_type_id)s
ORDER BY r.service_date DESC, r.odometer DESC
LIMIT 1
"""

INSERT_SQL = """
INSERT INTO reminders (vehicle_id, service_type_id, interval_km, interval_months,
                       notify_before_days, notify_before_km, start_date, start_odometer)
VALUES (%(vehicle_id)s, %(service_type_id)s, %(interval_km)s, %(interval_months)s,
        %(notify_before_days)s, %(notify_before_km)s, %(start_date)s, %(start_odometer)s)
RETURNING id
"""

OWN_SQL = """
SELECT rm.id, rm.service_type_id
FROM reminders rm
JOIN vehicles v ON v.id = rm.vehicle_id
WHERE rm.id = %(id)s AND v.user_id = %(uid)s
FOR UPDATE OF rm
"""

# a start mark left out keeps the one already stored
UPDATE_SQL = """
UPDATE reminders
SET interval_km = %(interval_km)s, interval_months = %(interval_months)s,
    notify_before_days = %(notify_before_days)s, notify_before_km = %(notify_before_km)s,
    start_date = coalesce(%(start_date)s::date, start_date),
    start_odometer = coalesce(%(start_odometer)s::integer, start_odometer)
WHERE id = %(id)s
"""

ACTIVE_SQL = """
UPDATE reminders SET is_active = %(active)s
WHERE id = %(id)s AND vehicle_id IN (SELECT id FROM vehicles WHERE user_id = %(uid)s)
RETURNING id
"""

DELETE_SQL = """
DELETE FROM reminders
WHERE id = %(id)s AND vehicle_id IN (SELECT id FROM vehicles WHERE user_id = %(uid)s)
RETURNING id
"""

VEHICLE_NOT_FOUND = ApiError(404, "VEHICLE_NOT_FOUND", "Không tìm thấy xe này.")
REMINDER_NOT_FOUND = ApiError(404, "REMINDER_NOT_FOUND", "Không tìm thấy nhắc lịch này.")
DUPLICATE_REMINDER = ApiError(409, "DUPLICATE_REMINDER", "Xe này đã có nhắc lịch cho việc bảo dưỡng này.")


def with_progress(row: dict) -> dict:
    return {**row, "progress": interval_used(row)}


def read_reminder(cur, reminder_id: int, uid: int) -> dict:
    row = cur.execute(ONE_SQL, {"id": reminder_id, "uid": uid}).fetchone()
    if row is None:
        raise REMINDER_NOT_FOUND
    return with_progress(row)


def require_vehicle(cur, vehicle_id: int, uid: int) -> dict:
    """Another user's vehicle is "not found" too (FR-25)."""
    vehicle = cur.execute(VEHICLE_SQL, {"id": vehicle_id, "uid": uid}).fetchone()
    if vehicle is None:
        raise VEHICLE_NOT_FOUND
    return vehicle


def check_service_type(cur, service_type_id: int, uid: int) -> None:
    found = cur.execute(TYPE_SQL, {"id": service_type_id, "uid": uid}).fetchone()
    if found is None:
        raise ApiError(422, "SERVICE_TYPE_NOT_FOUND", "Việc bảo dưỡng không còn trong danh mục. Hãy chọn lại.")
    if not found["is_active"]:
        raise ApiError(422, "SERVICE_TYPE_INACTIVE", "Việc bảo dưỡng này đã ngừng dùng. Hãy chọn việc khác.")


def start_mark(cur, vehicle: dict, body: ReminderIn) -> tuple:
    """BR-07: with no start mark given, count from the last time this service was done on the vehicle,
    else from today and the vehicle's odometer. A half-given mark is completed from today and the odometer."""
    if body.start_date is None and body.start_odometer is None:
        last = cur.execute(
            LAST_RECORD_SQL, {"vehicle_id": vehicle["id"], "service_type_id": body.service_type_id}
        ).fetchone()
        if last:
            return last["service_date"], last["odometer"]
    start_date = body.start_date if body.start_date is not None else today_vn()
    start_odometer = body.start_odometer if body.start_odometer is not None else vehicle["current_odometer"]
    return start_date, start_odometer


def params(body: ReminderIn) -> dict:
    return {
        "interval_km": body.interval_km,
        "interval_months": body.interval_months,
        "notify_before_days": body.notify_before_days,
        "notify_before_km": body.notify_before_km,
    }


@router.get(
    "/vehicles/{vehicle_id}/reminders", response_model=list[ReminderDetailOut], responses={404: {"model": ErrorOut}}
)
def list_reminders(vehicle_id: int, user: CurrentUser):
    with db.pool.connection(timeout=5) as conn:
        cur = conn.cursor(row_factory=dict_row)
        require_vehicle(cur, vehicle_id, user["id"])
        rows = cur.execute(LIST_SQL, {"vehicle_id": vehicle_id, "uid": user["id"]}).fetchall()
    return [with_progress(row) for row in rows]


@router.post(
    "/vehicles/{vehicle_id}/reminders",
    response_model=ReminderDetailOut,
    status_code=201,
    responses={404: {"model": ErrorOut}, 409: {"model": ErrorOut}, 422: {"model": ErrorOut}},
)
def create_reminder(vehicle_id: int, body: ReminderIn, user: CurrentUser):
    with db.pool.connection(timeout=5) as conn:
        cur = conn.cursor(row_factory=dict_row)
        vehicle = require_vehicle(cur, vehicle_id, user["id"])
        if vehicle["is_archived"]:
            raise ApiError(409, "VEHICLE_ARCHIVED", "Xe đã lưu trữ. Hãy khôi phục xe trước khi đặt nhắc lịch.")
        check_service_type(cur, body.service_type_id, user["id"])
        start_date, start_odometer = start_mark(cur, vehicle, body)
        try:
            reminder_id = cur.execute(
                INSERT_SQL,
                {
                    **params(body),
                    "vehicle_id": vehicle_id,
                    "service_type_id": body.service_type_id,
                    "start_date": start_date,
                    "start_odometer": start_odometer,
                },
            ).fetchone()["id"]
        except UniqueViolation as err:
            raise DUPLICATE_REMINDER from err
        return read_reminder(cur, reminder_id, user["id"])


@router.get("/reminders/{reminder_id}", response_model=ReminderDetailOut, responses={404: {"model": ErrorOut}})
def read_one_reminder(reminder_id: int, user: CurrentUser):
    with db.pool.connection(timeout=5) as conn:
        return read_reminder(conn.cursor(row_factory=dict_row), reminder_id, user["id"])


@router.put(
    "/reminders/{reminder_id}",
    response_model=ReminderDetailOut,
    responses={404: {"model": ErrorOut}, 422: {"model": ErrorOut}},
)
def update_reminder(reminder_id: int, body: ReminderIn, user: CurrentUser):
    """The vehicle and the service type of a reminder never change: delete it and add another instead."""
    with db.pool.connection(timeout=5) as conn:
        cur = conn.cursor(row_factory=dict_row)
        own = cur.execute(OWN_SQL, {"id": reminder_id, "uid": user["id"]}).fetchone()
        if own is None:
            raise REMINDER_NOT_FOUND
        if own["service_type_id"] != body.service_type_id:
            raise ApiError(422, "SERVICE_TYPE_LOCKED", "Không đổi được việc bảo dưỡng của nhắc lịch. Hãy xóa và tạo nhắc lịch mới.")
        cur.execute(
            UPDATE_SQL,
            {**params(body), "id": reminder_id, "start_date": body.start_date, "start_odometer": body.start_odometer},
        )
        return read_reminder(cur, reminder_id, user["id"])


@router.patch("/reminders/{reminder_id}/active", response_model=ReminderDetailOut, responses={404: {"model": ErrorOut}})
def set_reminder_active(reminder_id: int, body: ActiveIn, user: CurrentUser):
    """Pause a reminder, or resume it (FR-14). A paused one leaves the dashboard but keeps its settings."""
    with db.pool.connection(timeout=5) as conn:
        cur = conn.cursor(row_factory=dict_row)
        if cur.execute(ACTIVE_SQL, {"id": reminder_id, "active": body.active, "uid": user["id"]}).fetchone() is None:
            raise REMINDER_NOT_FOUND
        return read_reminder(cur, reminder_id, user["id"])


@router.delete("/reminders/{reminder_id}", status_code=204, response_class=Response, responses={404: {"model": ErrorOut}})
def delete_reminder(reminder_id: int, user: CurrentUser):
    with db.pool.connection(timeout=5) as conn:
        if conn.cursor(row_factory=dict_row).execute(DELETE_SQL, {"id": reminder_id, "uid": user["id"]}).fetchone() is None:
            raise REMINDER_NOT_FOUND
    return Response(status_code=204)
