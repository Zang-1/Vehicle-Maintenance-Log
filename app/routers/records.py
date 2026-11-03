"""Maintenance records (M3, FR-06 → FR-10).

A record is saved with its items in ONE transaction: the pool's connection block commits when the
request ends well and rolls everything back when an ApiError (or any error) leaves it, so a record
without items, or a raised odometer without a record, can never be stored.

BR-02 the vehicle's odometer is raised when the record's is higher, never lowered.
BR-03 date not in the future and BR-04 at least one item: checked by RecordIn (app/schemas.py).
BR-04 no two records with the same vehicle + date + odometer: the UNIQUE constraint, answered with 409.
BR-05 line total = quantity x unit price and the total of a record are computed by the database.
FR-15 nothing to do here: v_reminder_status reads the latest matching record, so reminders follow by themselves.
"""

import csv
import io
from datetime import date

from fastapi import APIRouter, Response
from psycopg.errors import UniqueViolation
from psycopg.rows import dict_row

from app import db
from app.auth import CurrentUser
from app.errors import ApiError
from app.schemas import ErrorOut, RecordIn, RecordListItem, RecordOut

router = APIRouter(prefix="/api", tags=["records"])

VEHICLE_SQL = "SELECT id, is_archived FROM vehicles WHERE id = %(id)s AND user_id = %(uid)s"

LIST_SQL = """
SELECT t.record_id, t.service_date, t.odometer, t.garage_name, t.note, t.item_count, t.total_cost,
       (SELECT string_agg(DISTINCT st.name, ', ')
          FROM maintenance_items i
          JOIN service_types st ON st.id = i.service_type_id
         WHERE i.record_id = t.record_id) AS items_summary
FROM v_record_totals t
WHERE t.vehicle_id = %(vehicle_id)s
  AND (%(from_date)s::date IS NULL OR t.service_date >= %(from_date)s::date)
  AND (%(to_date)s::date IS NULL OR t.service_date <= %(to_date)s::date)
ORDER BY t.service_date DESC, t.record_id DESC
"""

RECORD_SQL = """
SELECT t.record_id, t.vehicle_id, v.name AS vehicle_name, v.license_plate, t.service_date, t.odometer,
       t.garage_name, t.note, t.item_count, t.total_cost
FROM v_record_totals t
JOIN vehicles v ON v.id = t.vehicle_id
WHERE t.record_id = %(id)s AND v.user_id = %(uid)s
"""

ITEMS_SQL = """
SELECT i.id, i.service_type_id, st.name AS service_type_name, i.description, i.quantity, i.unit_price, i.line_total
FROM maintenance_items i
JOIN service_types st ON st.id = i.service_type_id
WHERE i.record_id = %(id)s
ORDER BY i.id
"""

CSV_SQL = """
SELECT r.service_date, r.odometer, r.garage_name, r.note,
       st.name AS service_type_name, i.description, i.quantity, i.unit_price, i.line_total
FROM maintenance_records r
JOIN maintenance_items i ON i.record_id = r.id
JOIN service_types st ON st.id = i.service_type_id
WHERE r.vehicle_id = %(vehicle_id)s
  AND (%(from_date)s::date IS NULL OR r.service_date >= %(from_date)s::date)
  AND (%(to_date)s::date IS NULL OR r.service_date <= %(to_date)s::date)
ORDER BY r.service_date DESC, r.id DESC, i.id
"""

# a default type (user_id NULL) or one of the user's own
TYPES_SQL = "SELECT id, is_active FROM service_types WHERE id = ANY(%(ids)s) AND (user_id IS NULL OR user_id = %(uid)s)"
USED_TYPES_SQL = "SELECT DISTINCT service_type_id FROM maintenance_items WHERE record_id = %(id)s"

INSERT_RECORD_SQL = """
INSERT INTO maintenance_records (vehicle_id, service_date, odometer, garage_name, note)
VALUES (%(vehicle_id)s, %(service_date)s, %(odometer)s, %(garage_name)s, %(note)s)
RETURNING id
"""

UPDATE_RECORD_SQL = """
UPDATE maintenance_records
SET service_date = %(service_date)s, odometer = %(odometer)s, garage_name = %(garage_name)s, note = %(note)s
WHERE id = %(id)s AND vehicle_id IN (SELECT id FROM vehicles WHERE user_id = %(uid)s)
RETURNING vehicle_id
"""

INSERT_ITEM_SQL = """
INSERT INTO maintenance_items (record_id, service_type_id, description, quantity, unit_price)
VALUES (%(record_id)s, %(service_type_id)s, %(description)s, %(quantity)s, %(unit_price)s)
"""

DELETE_ITEMS_SQL = "DELETE FROM maintenance_items WHERE record_id = %(id)s"
DELETE_RECORD_SQL = """
DELETE FROM maintenance_records
WHERE id = %(id)s AND vehicle_id IN (SELECT id FROM vehicles WHERE user_id = %(uid)s)
RETURNING id
"""

# BR-02: only ever raises the odometer. A record for an older date (higher or lower km) leaves it alone.
RAISE_ODOMETER_SQL = """
UPDATE vehicles SET current_odometer = %(odometer)s
WHERE id = %(vehicle_id)s AND current_odometer < %(odometer)s
"""

VEHICLE_NOT_FOUND = ApiError(404, "VEHICLE_NOT_FOUND", "Không tìm thấy xe này.")
RECORD_NOT_FOUND = ApiError(404, "RECORD_NOT_FOUND", "Không tìm thấy lần bảo dưỡng này.")
DUPLICATE_RECORD = ApiError(409, "DUPLICATE_RECORD", "Lần bảo dưỡng này đã được ghi trước đó (cùng xe, cùng ngày, cùng số km).")


def read_record(cur, record_id: int, uid: int) -> dict:
    record = cur.execute(RECORD_SQL, {"id": record_id, "uid": uid}).fetchone()
    if record is None:
        raise RECORD_NOT_FOUND
    record["items"] = cur.execute(ITEMS_SQL, {"id": record_id}).fetchall()
    return record


def require_vehicle(cur, vehicle_id: int, uid: int) -> dict:
    """Another user's vehicle is "not found" too (FR-25)."""
    vehicle = cur.execute(VEHICLE_SQL, {"id": vehicle_id, "uid": uid}).fetchone()
    if vehicle is None:
        raise VEHICLE_NOT_FOUND
    return vehicle


def check_service_types(cur, body: RecordIn, uid: int, already_used: set[int] = frozenset()) -> None:
    """Every item needs an existing, active service type. A type retired since (BR-09) may stay on a record
    that already had it, so editing an old record does not fail on it."""
    wanted = {item.service_type_id for item in body.items}
    found = {row["id"]: row["is_active"] for row in cur.execute(TYPES_SQL, {"ids": sorted(wanted), "uid": uid}).fetchall()}
    if wanted - found.keys():
        raise ApiError(422, "SERVICE_TYPE_NOT_FOUND", "Có việc bảo dưỡng không còn trong danh mục. Hãy chọn lại.")
    retired = {type_id for type_id, active in found.items() if not active} - set(already_used)
    if retired:
        raise ApiError(422, "SERVICE_TYPE_INACTIVE", "Có việc bảo dưỡng đã ngừng dùng. Hãy chọn việc khác.")


def insert_items(cur, record_id: int, body: RecordIn) -> None:
    cur.executemany(
        INSERT_ITEM_SQL,
        [
            {
                "record_id": record_id,
                "service_type_id": item.service_type_id,
                "description": item.description,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
            }
            for item in body.items
        ],
    )


def raise_odometer(cur, vehicle_id: int, odometer: int) -> None:
    cur.execute(RAISE_ODOMETER_SQL, {"vehicle_id": vehicle_id, "odometer": odometer})


@router.get("/vehicles/{vehicle_id}/records", response_model=list[RecordListItem], responses={404: {"model": ErrorOut}})
def list_records(vehicle_id: int, user: CurrentUser, from_date: date | None = None, to_date: date | None = None):
    with db.pool.connection(timeout=5) as conn:
        cur = conn.cursor(row_factory=dict_row)
        require_vehicle(cur, vehicle_id, user["id"])
        return cur.execute(LIST_SQL, {"vehicle_id": vehicle_id, "from_date": from_date, "to_date": to_date}).fetchall()


@router.post(
    "/vehicles/{vehicle_id}/records",
    response_model=RecordOut,
    status_code=201,
    responses={404: {"model": ErrorOut}, 409: {"model": ErrorOut}},
)
def create_record(vehicle_id: int, body: RecordIn, user: CurrentUser):
    with db.pool.connection(timeout=5) as conn:
        cur = conn.cursor(row_factory=dict_row)
        if require_vehicle(cur, vehicle_id, user["id"])["is_archived"]:
            raise ApiError(409, "VEHICLE_ARCHIVED", "Xe đã lưu trữ. Hãy khôi phục xe trước khi ghi bảo dưỡng.")
        check_service_types(cur, body, user["id"])
        try:
            record_id = cur.execute(
                INSERT_RECORD_SQL,
                {
                    "vehicle_id": vehicle_id,
                    "service_date": body.service_date,
                    "odometer": body.odometer,
                    "garage_name": body.garage_name,
                    "note": body.note,
                },
            ).fetchone()["id"]
        except UniqueViolation as err:
            raise DUPLICATE_RECORD from err
        insert_items(cur, record_id, body)
        raise_odometer(cur, vehicle_id, body.odometer)
        return read_record(cur, record_id, user["id"])


@router.get("/records/{record_id}", response_model=RecordOut, responses={404: {"model": ErrorOut}})
def read_one_record(record_id: int, user: CurrentUser):
    with db.pool.connection(timeout=5) as conn:
        return read_record(conn.cursor(row_factory=dict_row), record_id, user["id"])


@router.put("/records/{record_id}", response_model=RecordOut, responses={404: {"model": ErrorOut}, 409: {"model": ErrorOut}})
def update_record(record_id: int, body: RecordIn, user: CurrentUser):
    """Replaces the record and all its items. The vehicle of a record never changes."""
    with db.pool.connection(timeout=5) as conn:
        cur = conn.cursor(row_factory=dict_row)
        used = {row["service_type_id"] for row in cur.execute(USED_TYPES_SQL, {"id": record_id}).fetchall()}
        check_service_types(cur, body, user["id"], used)
        try:
            row = cur.execute(
                UPDATE_RECORD_SQL,
                {
                    "id": record_id,
                    "uid": user["id"],
                    "service_date": body.service_date,
                    "odometer": body.odometer,
                    "garage_name": body.garage_name,
                    "note": body.note,
                },
            ).fetchone()
        except UniqueViolation as err:
            raise DUPLICATE_RECORD from err
        if row is None:
            raise RECORD_NOT_FOUND
        cur.execute(DELETE_ITEMS_SQL, {"id": record_id})
        insert_items(cur, record_id, body)
        raise_odometer(cur, row["vehicle_id"], body.odometer)
        return read_record(cur, record_id, user["id"])


@router.delete("/records/{record_id}", status_code=204, response_class=Response, responses={404: {"model": ErrorOut}})
def delete_record(record_id: int, user: CurrentUser):
    """Items go with the record (ON DELETE CASCADE). The vehicle's odometer stays where it is (BR-02)."""
    with db.pool.connection(timeout=5) as conn:
        if conn.cursor(row_factory=dict_row).execute(DELETE_RECORD_SQL, {"id": record_id, "uid": user["id"]}).fetchone() is None:
            raise RECORD_NOT_FOUND
    return Response(status_code=204)


def csv_cell(value):
    """A text cell that starts with = + - @ would run as a formula in Excel; a leading quote keeps it text."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return "" if value is None else value


@router.get("/vehicles/{vehicle_id}/records.csv", responses={404: {"model": ErrorOut}})
def export_csv(vehicle_id: int, user: CurrentUser, from_date: date | None = None, to_date: date | None = None):
    """FR-10: one row per item, newest record first. Starts with a BOM so Excel reads the Vietnamese text."""
    with db.pool.connection(timeout=5) as conn:
        cur = conn.cursor(row_factory=dict_row)
        require_vehicle(cur, vehicle_id, user["id"])
        rows = cur.execute(CSV_SQL, {"vehicle_id": vehicle_id, "from_date": from_date, "to_date": to_date}).fetchall()
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["Ngày", "Số km", "Nơi làm", "Ghi chú", "Việc bảo dưỡng", "Mô tả", "Số lượng", "Đơn giá (đ)", "Thành tiền (đ)"])
    for r in rows:
        writer.writerow(
            [
                csv_cell(value)
                for value in (
                    r["service_date"].strftime("%d/%m/%Y"), r["odometer"], r["garage_name"], r["note"],
                    r["service_type_name"], r["description"], r["quantity"], r["unit_price"], r["line_total"],
                )
            ]
        )
    return Response(
        content="﻿" + out.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="lich-su-xe-{vehicle_id}.csv"'},
    )
