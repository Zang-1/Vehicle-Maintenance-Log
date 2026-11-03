"""Dashboard numbers (FR-16). Everything is read from the two views of doc 04."""

from fastapi import APIRouter, Query
from psycopg.rows import dict_row

from app import db
from app.auth import CurrentUser
from app.schemas import (
    CostByType,
    CostByVehicle,
    CostMonth,
    CostsOut,
    DashboardOut,
    DashboardVehicle,
    VehicleReminderSummary,
)

router = APIRouter(prefix="/api/stats", tags=["stats"])

VEHICLE_COUNT_SQL = "SELECT count(*) AS n FROM vehicles WHERE user_id = %(uid)s AND NOT is_archived"

COST_THIS_MONTH_SQL = """
SELECT coalesce(sum(total_cost), 0) AS total
FROM v_record_totals
WHERE service_date >= date_trunc('month', current_date)
  AND vehicle_id IN (SELECT id FROM vehicles WHERE user_id = %(uid)s)
"""

COST_THIS_YEAR_SQL = """
SELECT coalesce(sum(total_cost), 0) AS total
FROM v_record_totals
WHERE service_date >= date_trunc('year', current_date)
  AND vehicle_id IN (SELECT id FROM vehicles WHERE user_id = %(uid)s)
"""

ATTENTION_SQL = """
SELECT reminder_id, vehicle_id, vehicle_name, service_type_id, service_type_name,
       interval_km, interval_months, base_date, base_odometer,
       next_due_date, next_due_odometer, days_left, km_left, is_active, status
FROM v_reminder_status
WHERE is_active AND status <> 'OK'
  AND vehicle_id IN (SELECT id FROM vehicles WHERE user_id = %(uid)s)
ORDER BY (status = 'OVERDUE') DESC, days_left NULLS LAST, km_left NULLS LAST
"""

RECENT_RECORDS_SQL = """
SELECT t.record_id, t.vehicle_id, v.name AS vehicle_name, t.service_date, t.odometer,
       t.garage_name, t.item_count, t.total_cost,
       (SELECT string_agg(DISTINCT st.name, ', ')
          FROM maintenance_items i
          JOIN service_types st ON st.id = i.service_type_id
         WHERE i.record_id = t.record_id) AS items_summary
FROM v_record_totals t
JOIN vehicles v ON v.id = t.vehicle_id
WHERE v.user_id = %(uid)s
ORDER BY t.service_date DESC, t.record_id DESC
LIMIT 5
"""

VEHICLES_SQL = """
SELECT id, name, vehicle_type, license_plate, current_odometer
FROM vehicles
WHERE user_id = %(uid)s AND NOT is_archived
ORDER BY id
"""

ACTIVE_REMINDERS_SQL = """
SELECT vehicle_id, service_type_name, status, days_left, km_left,
       next_due_date, next_due_odometer, base_date, base_odometer, current_odometer, interval_km
FROM v_reminder_status
WHERE is_active AND vehicle_id IN (SELECT id FROM vehicles WHERE user_id = %(uid)s)
"""

STATUS_RANK = {"OVERDUE": 0, "DUE_SOON": 1, "OK": 2}


def interval_used(r: dict) -> float:
    """Share of the interval already used (0..1), the larger of time and distance."""
    shares = []
    if r["next_due_date"] is not None and r["days_left"] is not None:
        total_days = (r["next_due_date"] - r["base_date"]).days
        if total_days > 0:
            shares.append((total_days - r["days_left"]) / total_days)
    if r["interval_km"]:
        shares.append((r["current_odometer"] - r["base_odometer"]) / r["interval_km"])
    if r["status"] == "OVERDUE":
        shares.append(1.0)
    return round(min(1.0, max(0.0, max(shares, default=0.0))), 3)


def vehicle_cards(vehicles: list[dict], reminders: list[dict]) -> list[DashboardVehicle]:
    """Each vehicle with the reminder its card shows: the most urgent, else the next one due."""
    by_vehicle: dict[int, list[dict]] = {}
    for r in reminders:
        by_vehicle.setdefault(r["vehicle_id"], []).append(r)
    cards = []
    for v in vehicles:
        own = sorted(
            by_vehicle.get(v["id"], []),
            key=lambda r: (STATUS_RANK[r["status"]], r["days_left"] if r["days_left"] is not None else 10**9),
        )
        top = own[0] if own else None
        summary = None
        if top:
            summary = VehicleReminderSummary(
                service_type_name=top["service_type_name"],
                status=top["status"],
                days_left=top["days_left"],
                km_left=top["km_left"],
                next_due_date=top["next_due_date"],
                next_due_odometer=top["next_due_odometer"],
                progress=interval_used(top),
            )
        cards.append(DashboardVehicle(**v, reminder=summary))
    return cards


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(user: CurrentUser):
    mine = {"uid": user["id"]}
    with db.pool.connection(timeout=5) as conn:
        cur = conn.cursor(row_factory=dict_row)
        vehicle_count = cur.execute(VEHICLE_COUNT_SQL, mine).fetchone()["n"]
        cost_this_month = cur.execute(COST_THIS_MONTH_SQL, mine).fetchone()["total"]
        cost_this_year = cur.execute(COST_THIS_YEAR_SQL, mine).fetchone()["total"]
        attention = cur.execute(ATTENTION_SQL, mine).fetchall()
        recent = cur.execute(RECENT_RECORDS_SQL, mine).fetchall()
        vehicles = cur.execute(VEHICLES_SQL, mine).fetchall()
        reminders = cur.execute(ACTIVE_REMINDERS_SQL, mine).fetchall()
    return DashboardOut(
        vehicle_count=vehicle_count,
        cost_this_month=cost_this_month,
        cost_this_year=cost_this_year,
        attention_reminders=attention,
        recent_records=recent,
        vehicles=vehicle_cards(vehicles, reminders),
    )


# ---- Chi phí (FR-17, Khoa): a year or all time, all vehicles or one ----

COSTS_FILTER = """
(%(year)s::int IS NULL OR extract(year FROM service_date) = %(year)s::int)
AND (%(vehicle_id)s::bigint IS NULL OR vehicle_id = %(vehicle_id)s::bigint)
AND vehicle_id IN (SELECT id FROM vehicles WHERE user_id = %(uid)s)
"""

COSTS_TOTAL_SQL = f"""
SELECT coalesce(sum(total_cost), 0) AS grand_total, count(*) AS record_count,
       coalesce(sum(item_count), 0)::int AS item_count
FROM v_record_totals
WHERE {COSTS_FILTER}
"""

COSTS_MONTHLY_SQL = f"""
SELECT extract(month FROM service_date)::int AS month, sum(total_cost) AS total
FROM v_record_totals
WHERE {COSTS_FILTER}
GROUP BY 1
ORDER BY 1
"""

COSTS_BY_TYPE_SQL = f"""
SELECT st.id AS service_type_id, st.name AS service_type_name, sum(i.line_total) AS total
FROM maintenance_items i
JOIN v_record_totals r ON r.record_id = i.record_id
JOIN service_types st ON st.id = i.service_type_id
WHERE {COSTS_FILTER}
GROUP BY st.id, st.name
ORDER BY total DESC, st.name
"""

COSTS_BY_VEHICLE_SQL = f"""
SELECT v.id AS vehicle_id, v.name AS vehicle_name, v.vehicle_type, v.license_plate,
       count(*) AS record_count, sum(t.total_cost) AS total
FROM v_record_totals t
JOIN vehicles v ON v.id = t.vehicle_id
WHERE {COSTS_FILTER}
GROUP BY v.id
ORDER BY total DESC, v.id
"""


@router.get("/costs", response_model=CostsOut)
def costs(user: CurrentUser, vehicle_id: int | None = None, year: int | None = Query(default=None, ge=2000, le=2100)):
    params = {"year": year, "vehicle_id": vehicle_id, "uid": user["id"]}
    with db.pool.connection(timeout=5) as conn:
        cur = conn.cursor(row_factory=dict_row)
        totals = cur.execute(COSTS_TOTAL_SQL, params).fetchone()
        monthly = cur.execute(COSTS_MONTHLY_SQL, params).fetchall()
        by_type = cur.execute(COSTS_BY_TYPE_SQL, params).fetchall()
        by_vehicle = cur.execute(COSTS_BY_VEHICLE_SQL, params).fetchall()
    found = {row["month"]: row["total"] for row in monthly}
    return CostsOut(
        year=year,
        vehicle_id=vehicle_id,
        total=totals["grand_total"],
        record_count=totals["record_count"],
        item_count=totals["item_count"],
        months=[CostMonth(month=m, total=found.get(m, 0)) for m in range(1, 13)],
        by_service_type=[CostByType(**row) for row in by_type],
        by_vehicle=[CostByVehicle(**row) for row in by_vehicle],
    )