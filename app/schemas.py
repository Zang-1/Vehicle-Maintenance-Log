"""Pydantic models (doc 07, sections 6.1 and 6.2).

Each module adds its own models here (VehicleIn/Out for M2, RecordIn for M3, ...)
in its own pull request.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, StringConstraints


class RootOut(BaseModel):
    app: str
    version: str
    env: str
    message: str


class HealthOut(BaseModel):
    status: str


class HealthDbOut(BaseModel):
    db: str
    vehicles: int


class ErrorOut(BaseModel):
    """Body of every business error (404, 409, AI errors). 422 keeps FastAPI's own format."""

    error_code: str
    message: str


class ReminderStatus(str, Enum):
    OK = "OK"
    DUE_SOON = "DUE_SOON"
    OVERDUE = "OVERDUE"


class ReminderOut(BaseModel):
    """One row of v_reminder_status (BR-07, BR-08)."""

    reminder_id: int
    vehicle_id: int
    vehicle_name: str
    service_type_id: int
    service_type_name: str
    interval_km: int | None
    interval_months: int | None
    base_date: date
    base_odometer: int
    next_due_date: date | None
    next_due_odometer: int | None
    days_left: int | None
    km_left: int | None
    is_active: bool
    status: ReminderStatus


class RecordSummary(BaseModel):
    """One row of v_record_totals."""

    record_id: int
    service_date: date
    odometer: int
    garage_name: str | None
    item_count: int
    total_cost: Decimal


class DashboardRecord(RecordSummary):
    """RecordSummary plus what S01 shows next to it: the vehicle and the service types done."""

    vehicle_id: int
    vehicle_name: str
    items_summary: str | None


class VehicleReminderSummary(BaseModel):
    """The one reminder a home-screen vehicle card shows: the most urgent, else the next one due."""

    service_type_name: str
    status: ReminderStatus
    days_left: int | None
    km_left: int | None
    next_due_date: date | None
    next_due_odometer: int | None
    progress: float  # 0..1 share of the interval already used, the larger of time and distance


class DashboardVehicle(BaseModel):
    id: int
    name: str
    vehicle_type: str
    license_plate: str | None
    current_odometer: int
    reminder: VehicleReminderSummary | None


class DashboardOut(BaseModel):
    vehicle_count: int
    cost_this_month: Decimal
    cost_this_year: Decimal
    attention_reminders: list[ReminderOut]
    recent_records: list[DashboardRecord]
    vehicles: list[DashboardVehicle]


class DiagnoseIn(BaseModel):
    """FR-18. Too short or too long gets FastAPI's 422 before any AI call."""

    symptom_text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=1000)]


class DiagnoseOut(BaseModel):
    suggestion: str


class DiagnosisOut(BaseModel):
    """One row of the diagnoses table (FR-21): successful calls and failed ones alike."""

    id: int
    created_at: datetime
    symptom_text: str
    status: str  # OK | FAILED
    ai_suggestion: str | None
    urgency_level: str | None  # LOW | MEDIUM | HIGH
    error_code: str | None  # NO_KEY | RATE_LIMITED | TIMEOUT | UPSTREAM_ERROR
    model: str | None
