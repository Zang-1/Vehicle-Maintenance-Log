"""Service types (FR-11, FR-12). The forms of M3 and M5 pick from this list.

A type that records or reminders point at can only be retired (is_active = false, BR-09);
a type nobody used yet can be deleted.
"""

from fastapi import APIRouter, Response
from psycopg.errors import ForeignKeyViolation, RestrictViolation, UniqueViolation
from psycopg.rows import dict_row

from app import db
from app.errors import ApiError
from app.schemas import ActiveIn, ErrorOut, ServiceTypeIn, ServiceTypeOut, VehicleType

router = APIRouter(prefix="/api/service-types", tags=["service-types"])

# used_count = record items + reminders that point at the type; above 0 it can only be retired.
SELECT_SQL = """
SELECT id, name, description, applies_to, default_interval_km, default_interval_months, is_active,
       (SELECT count(*) FROM maintenance_items WHERE service_type_id = service_types.id)
       + (SELECT count(*) FROM reminders WHERE service_type_id = service_types.id) AS used_count
FROM service_types
"""

# vehicle_type: a motorbike sees "MOTORBIKE" and "ALL" types, a car "CAR" and "ALL"; OTHER sees only "ALL".
LIST_SQL = SELECT_SQL + """
WHERE (%(active)s::boolean IS NULL OR is_active = %(active)s::boolean)
  AND (%(vehicle_type)s::text IS NULL OR applies_to IN ('ALL', %(vehicle_type)s::text))
ORDER BY name
"""

ONE_SQL = SELECT_SQL + " WHERE id = %(id)s"

INSERT_SQL = """
INSERT INTO service_types (name, description, applies_to, default_interval_km, default_interval_months)
VALUES (%(name)s, %(description)s, %(applies_to)s, %(default_interval_km)s, %(default_interval_months)s)
RETURNING id
"""

UPDATE_SQL = """
UPDATE service_types
SET name = %(name)s, description = %(description)s, applies_to = %(applies_to)s,
    default_interval_km = %(default_interval_km)s, default_interval_months = %(default_interval_months)s
WHERE id = %(id)s
"""

ACTIVE_SQL = "UPDATE service_types SET is_active = %(active)s WHERE id = %(id)s"
DELETE_SQL = "DELETE FROM service_types WHERE id = %(id)s"

NOT_FOUND = ApiError(404, "SERVICE_TYPE_NOT_FOUND", "Không tìm thấy loại việc này.")
DUPLICATE_NAME = ApiError(409, "DUPLICATE_SERVICE_TYPE", "Tên loại việc này đã có trong danh mục.")
IN_USE = ApiError(409, "SERVICE_TYPE_IN_USE", "Loại việc này đã được dùng nên chỉ ngừng dùng được, không xóa hẳn.")


def params(body: ServiceTypeIn) -> dict:
    data = body.model_dump()
    data["applies_to"] = body.applies_to.value
    return data


def get_service_type(cur, service_type_id: int) -> dict:
    row = cur.execute(ONE_SQL, {"id": service_type_id}).fetchone()
    if row is None:
        raise NOT_FOUND
    return row


@router.get("", response_model=list[ServiceTypeOut])
def list_service_types(active: bool | None = None, vehicle_type: VehicleType | None = None):
    query = {"active": active, "vehicle_type": vehicle_type.value if vehicle_type else None}
    with db.pool.connection(timeout=5) as conn:
        return conn.cursor(row_factory=dict_row).execute(LIST_SQL, query).fetchall()


@router.get("/{service_type_id}", response_model=ServiceTypeOut, responses={404: {"model": ErrorOut}})
def read_service_type(service_type_id: int):
    with db.pool.connection(timeout=5) as conn:
        return get_service_type(conn.cursor(row_factory=dict_row), service_type_id)


@router.post("", response_model=ServiceTypeOut, status_code=201, responses={409: {"model": ErrorOut}})
def create_service_type(body: ServiceTypeIn):
    with db.pool.connection(timeout=5) as conn:
        cur = conn.cursor(row_factory=dict_row)
        try:
            new_id = cur.execute(INSERT_SQL, params(body)).fetchone()["id"]
        except UniqueViolation as err:  # service_types.name is UNIQUE
            raise DUPLICATE_NAME from err
        return get_service_type(cur, new_id)


@router.put(
    "/{service_type_id}",
    response_model=ServiceTypeOut,
    responses={404: {"model": ErrorOut}, 409: {"model": ErrorOut}},
)
def update_service_type(service_type_id: int, body: ServiceTypeIn):
    with db.pool.connection(timeout=5) as conn:
        cur = conn.cursor(row_factory=dict_row)
        get_service_type(cur, service_type_id)
        try:
            cur.execute(UPDATE_SQL, {**params(body), "id": service_type_id})
        except UniqueViolation as err:
            raise DUPLICATE_NAME from err
        return get_service_type(cur, service_type_id)


@router.patch("/{service_type_id}/active", response_model=ServiceTypeOut, responses={404: {"model": ErrorOut}})
def set_service_type_active(service_type_id: int, body: ActiveIn):
    """Retire a service type, or bring it back (FR-12, BR-09)."""
    with db.pool.connection(timeout=5) as conn:
        cur = conn.cursor(row_factory=dict_row)
        get_service_type(cur, service_type_id)
        cur.execute(ACTIVE_SQL, {"id": service_type_id, "active": body.active})
        return get_service_type(cur, service_type_id)


@router.delete(
    "/{service_type_id}",
    status_code=204,
    response_class=Response,
    responses={404: {"model": ErrorOut}, 409: {"model": ErrorOut}},
)
def delete_service_type(service_type_id: int):
    """Only a type nobody used yet can be deleted; otherwise retire it (BR-09)."""
    with db.pool.connection(timeout=5) as conn:
        cur = conn.cursor(row_factory=dict_row)
        if get_service_type(cur, service_type_id)["used_count"]:
            raise IN_USE
        try:
            cur.execute(DELETE_SQL, {"id": service_type_id})
        except (ForeignKeyViolation, RestrictViolation) as err:  # used by a record added meanwhile
            raise IN_USE from err
    return Response(status_code=204)