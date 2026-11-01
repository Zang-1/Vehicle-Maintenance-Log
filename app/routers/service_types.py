"""Service types, read side only (FR-11). The forms of M3 and M5 pick from this list.

Adding, editing and retiring service types (FR-12) is M4 (Khoa): put those routes in this file.
"""

from fastapi import APIRouter
from psycopg.rows import dict_row

from app import db
from app.schemas import ServiceTypeOut, VehicleType

router = APIRouter(prefix="/api/service-types", tags=["service-types"])

# vehicle_type: a motorbike sees "MOTORBIKE" and "ALL" types, a car "CAR" and "ALL"; OTHER sees only "ALL".
LIST_SQL = """
SELECT id, name, description, applies_to, default_interval_km, default_interval_months, is_active
FROM service_types
WHERE (%(active)s::boolean IS NULL OR is_active = %(active)s::boolean)
  AND (%(vehicle_type)s::text IS NULL OR applies_to IN ('ALL', %(vehicle_type)s::text))
ORDER BY name
"""


@router.get("", response_model=list[ServiceTypeOut])
def list_service_types(active: bool | None = None, vehicle_type: VehicleType | None = None):
    params = {"active": active, "vehicle_type": vehicle_type.value if vehicle_type else None}
    with db.pool.connection(timeout=5) as conn:
        return conn.cursor(row_factory=dict_row).execute(LIST_SQL, params).fetchall()
