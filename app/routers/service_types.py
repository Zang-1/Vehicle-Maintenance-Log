"""Service types (FR-11, FR-12). The forms of M3 and M5 pick from this list.

Default types (user_id NULL) are shared and read-only; each user can add, edit, retire and delete their own.

A type that records or reminders point at can only be retired (is_active = false, BR-09);
a type nobody used yet can be deleted.
"""

from fastapi import APIRouter, Response
from psycopg.errors import ForeignKeyViolation, RestrictViolation, UniqueViolation
from psycopg.rows import dict_row

from app import db
from app.auth import CurrentUser
from app.errors import ApiError
from app.schemas import ActiveIn, ErrorOut, ServiceTypeIn, ServiceTypeOut, VehicleType

router = APIRouter(prefix="/api/service-types", tags=["service-types"])

# used_count = the user's record items + reminders that point at the type; above 0 it can only be retired.
SELECT_SQL = """
SELECT id, name, description, applies_to, default_interval_km, default_interval_months, is_active,
       user_id IS NULL AS is_builtin,
       (SELECT count(*) FROM maintenance_items i
          JOIN maintenance_records r ON r.id = i.record_id
          JOIN vehicles v ON v.id = r.vehicle_id
         WHERE i.service_type_id = service_types.id AND v.user_id = %(uid)s)
       + (SELECT count(*) FROM reminders rm
          JOIN vehicles v ON v.id = rm.vehicle_id
         WHERE rm.service_type_id = service_types.id AND v.user_id = %(uid)s) AS used_count
FROM service_types
"""

# vehicle_type: a motorbike sees "MOTORBIKE" and "ALL" types, a car "CAR" and "ALL"; OTHER sees only "ALL".
LIST_SQL = SELECT_SQL + """
WHERE (user_id IS NULL OR user_id = %(uid)s)
  AND (%(active)s::boolean IS NULL OR is_active = %(active)s::boolean)
  AND (%(vehicle_type)s::text IS NULL OR applies_to IN ('ALL', %(vehicle_type)s::text))
ORDER BY name
"""

ONE_SQL = SELECT_SQL + " WHERE id = %(id)s AND (user_id IS NULL OR user_id = %(uid)s)"

INSERT_SQL = """
INSERT INTO service_types (user_id, name, description, applies_to, default_interval_km, default_interval_months)
VALUES (%(uid)s, %(name)s, %(description)s, %(applies_to)s, %(default_interval_km)s, %(default_interval_months)s)
RETURNING id
"""

UPDATE_SQL = """
UPDATE service_types
SET name = %(name)s, description = %(description)s, applies_to = %(applies_to)s,
    default_interval_km = %(default_interval_km)s, default_interval_months = %(default_interval_months)s
WHERE id = %(id)s AND user_id = %(uid)s
"""

ACTIVE_SQL = "UPDATE service_types SET is_active = %(active)s WHERE id = %(id)s AND user_id = %(uid)s"
DELETE_SQL = "DELETE FROM service_types WHERE id = %(id)s AND user_id = %(uid)s"

# A personal type may not take the name of a default one either: the pickers would show it twice.
NAME_TAKEN_SQL = """
SELECT 1 FROM service_types
WHERE lower(name) = lower(%(name)s) AND (user_id IS NULL OR user_id = %(uid)s) AND id <> %(id)s
"""

NOT_FOUND = ApiError(404, "SERVICE_TYPE_NOT_FOUND", "Không tìm thấy loại việc này.")
DUPLICATE_NAME = ApiError(409, "DUPLICATE_SERVICE_TYPE", "Tên loại việc này đã có trong danh mục.")
IN_USE = ApiError(409, "SERVICE_TYPE_IN_USE", "Loại việc này đã được dùng nên chỉ ngừng dùng được, không xóa hẳn.")
BUILTIN = ApiError(403, "BUILTIN_SERVICE_TYPE", "Đây là loại việc mặc định nên không sửa được. Hãy thêm loại việc riêng của bạn.")


def params(body: ServiceTypeIn) -> dict:
    data = body.model_dump()
    data["applies_to"] = body.applies_to.value
    return data


def get_service_type(cur, service_type_id: int, uid: int) -> dict:
    row = cur.execute(ONE_SQL, {"id": service_type_id, "uid": uid}).fetchone()
    if row is None:
        raise NOT_FOUND
    return row


def own_service_type(cur, service_type_id: int, uid: int) -> dict:
    row = get_service_type(cur, service_type_id, uid)
    if row["is_builtin"]:
        raise BUILTIN
    return row


def check_name_free(cur, name: str, uid: int, service_type_id: int = 0) -> None:
    if cur.execute(NAME_TAKEN_SQL, {"name": name, "uid": uid, "id": service_type_id}).fetchone():
        raise DUPLICATE_NAME


@router.get("", response_model=list[ServiceTypeOut])
def list_service_types(user: CurrentUser, active: bool | None = None, vehicle_type: VehicleType | None = None):
    query = {"active": active, "vehicle_type": vehicle_type.value if vehicle_type else None, "uid": user["id"]}
    with db.pool.connection(timeout=5) as conn:
        return conn.cursor(row_factory=dict_row).execute(LIST_SQL, query).fetchall()


@router.get("/{service_type_id}", response_model=ServiceTypeOut, responses={404: {"model": ErrorOut}})
def read_service_type(service_type_id: int, user: CurrentUser):
    with db.pool.connection(timeout=5) as conn:
        return get_service_type(conn.cursor(row_factory=dict_row), service_type_id, user["id"])


@router.post("", response_model=ServiceTypeOut, status_code=201, responses={409: {"model": ErrorOut}})
def create_service_type(body: ServiceTypeIn, user: CurrentUser):
    with db.pool.connection(timeout=5) as conn:
        cur = conn.cursor(row_factory=dict_row)
        check_name_free(cur, body.name, user["id"])
        try:
            new_id = cur.execute(INSERT_SQL, {**params(body), "uid": user["id"]}).fetchone()["id"]
        except UniqueViolation as err:  # (user_id, name) is UNIQUE: a double click
            raise DUPLICATE_NAME from err
        return get_service_type(cur, new_id, user["id"])


@router.put(
    "/{service_type_id}",
    response_model=ServiceTypeOut,
    responses={404: {"model": ErrorOut}, 409: {"model": ErrorOut}},
)
def update_service_type(service_type_id: int, body: ServiceTypeIn, user: CurrentUser):
    with db.pool.connection(timeout=5) as conn:
        cur = conn.cursor(row_factory=dict_row)
        own_service_type(cur, service_type_id, user["id"])
        check_name_free(cur, body.name, user["id"], service_type_id)
        try:
            cur.execute(UPDATE_SQL, {**params(body), "id": service_type_id, "uid": user["id"]})
        except UniqueViolation as err:
            raise DUPLICATE_NAME from err
        return get_service_type(cur, service_type_id, user["id"])


@router.patch("/{service_type_id}/active", response_model=ServiceTypeOut, responses={404: {"model": ErrorOut}})
def set_service_type_active(service_type_id: int, body: ActiveIn, user: CurrentUser):
    """Retire a service type, or bring it back (FR-12, BR-09)."""
    with db.pool.connection(timeout=5) as conn:
        cur = conn.cursor(row_factory=dict_row)
        own_service_type(cur, service_type_id, user["id"])
        cur.execute(ACTIVE_SQL, {"id": service_type_id, "active": body.active, "uid": user["id"]})
        return get_service_type(cur, service_type_id, user["id"])


@router.delete(
    "/{service_type_id}",
    status_code=204,
    response_class=Response,
    responses={404: {"model": ErrorOut}, 409: {"model": ErrorOut}},
)
def delete_service_type(service_type_id: int, user: CurrentUser):
    """Only a type nobody used yet can be deleted; otherwise retire it (BR-09)."""
    with db.pool.connection(timeout=5) as conn:
        cur = conn.cursor(row_factory=dict_row)
        if own_service_type(cur, service_type_id, user["id"])["used_count"]:
            raise IN_USE
        try:
            cur.execute(DELETE_SQL, {"id": service_type_id, "uid": user["id"]})
        except (ForeignKeyViolation, RestrictViolation) as err:  # used by a record added meanwhile
            raise IN_USE from err
    return Response(status_code=204)