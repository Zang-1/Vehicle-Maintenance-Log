"""Dashboard numbers (FR-16). Everything is read from the two views of doc 04."""

from fastapi import APIRouter
from psycopg.rows import dict_row

from app import db
from app.schemas import DashboardOut

router = APIRouter(prefix="/api/stats", tags=["stats"])

VEHICLE_COUNT_SQL = "SELECT count(*) AS n FROM vehicles WHERE NOT is_archived"

COST_THIS_MONTH_SQL = """
SELECT coalesce(sum(total_cost), 0) AS total
FROM v_record_totals
WHERE service_date >= date_trunc('month', current_date)
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


@router.get("/dashboard", response_model=DashboardOut)
def dashboard():
    with db.pool.connection(timeout=5) as conn:
        cur = conn.cursor(row_factory=dict_row)
        vehicle_count = cur.execute(VEHICLE_COUNT_SQL).fetchone()["n"]
        cost_this_month = cur.execute(COST_THIS_MONTH_SQL).fetchone()["total"]
        attention = cur.execute(ATTENTION_SQL).fetchall()
        recent = cur.execute(RECENT_RECORDS_SQL).fetchall()
    return DashboardOut(
        vehicle_count=vehicle_count,
        cost_this_month=cost_this_month,
        attention_reminders=attention,
        recent_records=recent,
    )
