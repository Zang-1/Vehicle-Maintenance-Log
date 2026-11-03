"""Vehicles (M2, FR-01 → FR-05).

Business rules kept here: BR-01 unique plate (409), BR-02 odometer never goes down (422),
BR-09 a vehicle with history can only be archived (409 on delete).
"""

from typing import Literal

import psycopg
from fastapi import APIRouter, Response
from psycopg.errors import ForeignKeyViolation, UniqueViolation
from psycopg.rows import dict_row

from app import db
from app.auth import CurrentUser
from app.errors import ApiError
from app.schemas import ArchiveIn, ErrorOut, VehicleIn, VehicleOut

router = APIRouter(prefix="/api/vehicles", tags=["vehicles"])

# A vehicle with what its card shows: the history totals (v_record_totals, BR-05) and the number of
# reminders that need attention (v_reminder_status, BR-08). %(archived)s is NULL for "all".
SELECT_SQL = """
SELECT v.id, v.name, v.vehicle_type, v.brand, v.model, v.manufacture_year, v.license_plate,
       v.current_odometer, v.purchase_date, v.is_archived, v.created_at,
       coalesce(r.record_count, 0) AS record_count,
       r.last_service_date,
       coalesce(r.total_cost, 0) AS total_cost,
       coalesce(s.overdue_count, 0) AS overdue_count,
       coalesce(s.due_soon_count, 0) AS due_soon_count
FROM vehicles v
LEFT JOIN (
    SELECT vehicle_id, count(*) AS record_count, max(service_date) AS last_service_date, sum(total_cost) AS total_cost
    FROM v_record_totals
    GROUP BY vehicle_id
) r ON r.vehicle_id = v.id
LEFT JOIN (
    SELECT vehicle_id,
           count(*) FILTER (WHERE status = 'OVERDUE') AS overdue_count,
           count(*) FILTER (WHERE status = 'DUE_SOON') AS due_soon_count
    FROM v_reminder_status
    WHERE is_active
    GROUP BY vehicle_id
) s ON s.vehicle_id = v.id
"""

LIST_SQL = SELECT_SQL + """
WHERE v.user_id = %(uid)s
  AND (%(archived)s::boolean IS NULL OR v.is_archived = %(archived)s::boolean)
ORDER BY v.is_archived, v.id
"""

ONE_SQL = SELECT_SQL + " WHERE v.id = %(id)s AND v.user_id = %(uid)s"

INSERT_SQL = """
INSERT INTO vehicles (user_id, name, vehicle_type, brand, model, manufacture_year, license_plate, current_odometer, purchase_date)
VALUES (%(uid)s, %(name)s, %(vehicle_type)s, %(brand)s, %(model)s, %(manufacture_year)s, %(license_plate)s,
        %(current_odometer)s, %(purchase_date)s)
RETURNING id
"""

UPDATE_SQL = """
UPDATE vehicles
SET name = %(name)s, vehicle_type = %(vehicle_type)s, brand = %(brand)s, model = %(model)s,
    manufacture_year = %(manufacture_year)s, license_plate = %(license_plate)s,
    current_odometer = %(current_odometer)s, purchase_date = %(purchase_date)s
WHERE id = %(id)s
"""

ODOMETER_SQL = "SELECT current_odometer FROM vehicles WHERE id = %(id)s AND user_id = %(uid)s FOR UPDATE"
ARCHIVE_SQL = "UPDATE vehicles SET is_archived = %(archived)s WHERE id = %(id)s"
COUNT_RECORDS_SQL = "SELECT count(*) AS n FROM maintenance_records WHERE vehicle_id = %(id)s"
DELETE_SQL = "DELETE FROM vehicles WHERE id = %(id)s"

NOT_FOUND = ApiError(404, "VEHICLE_NOT_FOUND", "Không tìm thấy xe này.")
DUPLICATE_PLATE = ApiError(409, "DUPLICATE_PLATE", "Biển số này đã có trong danh sách xe của bạn.")


def params(body: VehicleIn) -> dict:
    data = body.model_dump()
    data["vehicle_type"] = body.vehicle_type.value
    return data


def get_vehicle(cur, vehicle_id: int, uid: int) -> dict:
    """Another user's vehicle is "not found" too: never confirm that an id exists (FR-25)."""
    row = cur.execute(ONE_SQL, {"id": vehicle_id, "uid": uid}).fetchone()
    if row is None:
        raise NOT_FOUND
    return row


@router.get("", response_model=list[VehicleOut])
def list_vehicles(user: CurrentUser, archived: Literal["active", "archived", "all"] = "active"):
    flag = {"active": False, "archived": True, "all": None}[archived]
    with db.pool.connection(timeout=5) as conn:
        return conn.cursor(row_factory=dict_row).execute(LIST_SQL, {"archived": flag, "uid": user["id"]}).fetchall()


@router.post("", response_model=VehicleOut, status_code=201, responses={409: {"model": ErrorOut}})
def create_vehicle(body: VehicleIn, user: CurrentUser):
    with db.pool.connection(timeout=5) as conn:
        cur = conn.cursor(row_factory=dict_row)
        try:
            new_id = cur.execute(INSERT_SQL, {**params(body), "uid": user["id"]}).fetchone()["id"]
        except UniqueViolation as err:  # (user_id, license_plate) is UNIQUE (BR-01)
            raise DUPLICATE_PLATE from err
        return get_vehicle(cur, new_id, user["id"])


@router.get("/{vehicle_id}", response_model=VehicleOut, responses={404: {"model": ErrorOut}})
def read_vehicle(vehicle_id: int, user: CurrentUser):
    with db.pool.connection(timeout=5) as conn:
        return get_vehicle(conn.cursor(row_factory=dict_row), vehicle_id, user["id"])


@router.put("/{vehicle_id}", response_model=VehicleOut, responses={404: {"model": ErrorOut}, 409: {"model": ErrorOut}})
def update_vehicle(vehicle_id: int, body: VehicleIn, user: CurrentUser):
    with db.pool.connection(timeout=5) as conn:
        cur = conn.cursor(row_factory=dict_row)
        current = cur.execute(ODOMETER_SQL, {"id": vehicle_id, "uid": user["id"]}).fetchone()
        if current is None:
            raise NOT_FOUND
        if body.current_odometer < current["current_odometer"]:  # BR-02
            raise ApiError(
                422,
                "ODOMETER_DECREASE",
                f"Số km không được nhỏ hơn số hiện tại ({current['current_odometer']:,} km).".replace(",", "."),
            )
        try:
            cur.execute(UPDATE_SQL, {**params(body), "id": vehicle_id})
        except UniqueViolation as err:
            raise DUPLICATE_PLATE from err
        return get_vehicle(cur, vehicle_id, user["id"])


@router.patch("/{vehicle_id}/archive", response_model=VehicleOut, responses={404: {"model": ErrorOut}})
def archive_vehicle(vehicle_id: int, user: CurrentUser, body: ArchiveIn | None = None):
    """Hide a sold vehicle but keep its history (FR-05). {"archived": false} brings it back."""
    archived = True if body is None else body.archived
    with db.pool.connection(timeout=5) as conn:
        cur = conn.cursor(row_factory=dict_row)
        get_vehicle(cur, vehicle_id, user["id"])
        cur.execute(ARCHIVE_SQL, {"id": vehicle_id, "archived": archived})
        return get_vehicle(cur, vehicle_id, user["id"])


@router.delete(
    "/{vehicle_id}",
    status_code=204,
    response_class=Response,
    responses={404: {"model": ErrorOut}, 409: {"model": ErrorOut}},
)
def delete_vehicle(vehicle_id: int, user: CurrentUser):
    """Only a vehicle without history can be deleted (BR-09); otherwise archive it."""
    has_history = ApiError(409, "HAS_HISTORY", "Xe đã có lịch sử bảo dưỡng nên chỉ lưu trữ được, không xóa hẳn.")
    with db.pool.connection(timeout=5) as conn:
        cur = conn.cursor(row_factory=dict_row)
        get_vehicle(cur, vehicle_id, user["id"])
        if cur.execute(COUNT_RECORDS_SQL, {"id": vehicle_id}).fetchone()["n"]:
            raise has_history
        try:
            cur.execute(DELETE_SQL, {"id": vehicle_id})
        except (ForeignKeyViolation, psycopg.errors.RestrictViolation) as err:  # a record added meanwhile
            raise has_history from err
    return Response(status_code=204)
