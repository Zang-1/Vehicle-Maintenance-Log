"""Dashboard numbers (FR-16). Everything is read from the two views of doc 04."""

from fastapi import APIRouter
from psycopg.rows import dict_row

from app import db
from app.schemas import DashboardOut, DashboardVehicle, VehicleReminderSummary

router = APIRouter(prefix="/api/stats", tags=["stats"])

VEHICLE_COUNT_SQL = "SELECT count(*) AS n FROM vehicles WHERE NOT is_archived"

COST_THIS_MONTH_SQL = """
SELECT coalesce(sum(total_cost), 0) AS total
FROM v_record_totals
WHERE service_date >= date_trunc('month', current_date)
"""

COST_THIS_YEAR_SQL = """
SELECT coalesce(sum(total_cost), 0) AS total
FROM v_record_totals
WHERE service_date >= date_trunc('year', current_date)
"""

ATTENTION_SQL = """
SELECT reminder_id, vehicle_id, vehicle_name, service_type_id, service_type_name,
       interval_km, interval_months, base_date, base_odometer,
       next_due_date, next_due_odometer, days_left, km_left, is_active, status
FROM v_reminder_status
WHERE is_active AND status <> 'OK'
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
ORDER BY t.service_date DESC, t.record_id DESC
LIMIT 5
"""

VEHICLES_SQL = """
SELECT id, name, vehicle_type, license_plate, current_odometer
FROM vehicles
WHERE NOT is_archived
ORDER BY id
"""

ACTIVE_REMINDERS_SQL = """
SELECT vehicle_id, service_type_name, status, days_left, km_left,
       next_due_date, next_due_odometer, base_date, base_odometer, current_odometer, interval_km
FROM v_reminder_status
WHERE is_active
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
def dashboard():
    with db.pool.connection(timeout=5) as conn:
        cur = conn.cursor(row_factory=dict_row)
        vehicle_count = cur.execute(VEHICLE_COUNT_SQL).fetchone()["n"]
        cost_this_month = cur.execute(COST_THIS_MONTH_SQL).fetchone()["total"]
        cost_this_year = cur.execute(COST_THIS_YEAR_SQL).fetchone()["total"]
        attention = cur.execute(ATTENTION_SQL).fetchall()
        recent = cur.execute(RECENT_RECORDS_SQL).fetchall()
        vehicles = cur.execute(VEHICLES_SQL).fetchall()
        reminders = cur.execute(ACTIVE_REMINDERS_SQL).fetchall()
    return DashboardOut(
        vehicle_count=vehicle_count,
        cost_this_month=cost_this_month,
        cost_this_year=cost_this_year,
        attention_reminders=attention,
        recent_records=recent,
        vehicles=vehicle_cards(vehicles, reminders),
    )
