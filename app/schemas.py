"""Pydantic models (doc 07, sections 6.1 and 6.2).

Each module adds its own models here (VehicleIn/Out for M2, RecordIn for M3, ...)
in its own pull request.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Annotated

from pydantic import (
    BaseModel,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

VIETNAM = timezone(timedelta(hours=7))  # no daylight saving; zoneinfo would need the tzdata package in the slim image


def today_vn() -> date:
    """Today for the user. The server runs on UTC, which is still yesterday in Vietnam before 07:00 (BR-03)."""
    return datetime.now(VIETNAM).date()


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


# ---------- Tài khoản (FR-23, FR-24) ----------

Email = Annotated[
    str, StringConstraints(strip_whitespace=True, to_lower=True, min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
]


class RegisterIn(BaseModel):
    """BR-11 one account per email (lower case), BR-12 password of 8 to 128 characters."""

    email: Email
    display_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
    password: Annotated[str, StringConstraints(min_length=8, max_length=128)]


class LoginIn(BaseModel):
    email: Email
    password: Annotated[str, StringConstraints(min_length=1, max_length=128)]


class UserOut(BaseModel):
    id: int
    email: str
    display_name: str


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
    vehicle_id: Annotated[int, Field(gt=0)] | None = None  # FR-18: xe được chọn; None = hỏi chung


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


# ---------- M2 Xe (Lâm) ----------


class VehicleType(str, Enum):
    MOTORBIKE = "MOTORBIKE"
    CAR = "CAR"
    OTHER = "OTHER"


def blank_to_none(value):
    """An empty text box means "not given": the database stores NULL, not an empty string."""
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


class VehicleIn(BaseModel):
    """FR-01, FR-04. Only name, type and odometer are required; the rest is optional (docs/PHAN-CONG.md §2.1)."""

    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    vehicle_type: VehicleType
    brand: Annotated[str, StringConstraints(max_length=50)] | None = None
    model: Annotated[str, StringConstraints(max_length=50)] | None = None
    manufacture_year: Annotated[int, Field(ge=1950, le=2100)] | None = None
    license_plate: Annotated[str, StringConstraints(max_length=20)] | None = None
    current_odometer: Annotated[int, Field(ge=0, le=10_000_000)] = 0
    purchase_date: date | None = None

    @field_validator("brand", "model", "license_plate", mode="before")
    @classmethod
    def empty_is_none(cls, value):
        return blank_to_none(value)

    @field_validator("license_plate")
    @classmethod
    def plate_upper(cls, value):
        # BR-01: "59x1-123.45" and "59X1-123.45" are the same plate
        return value.upper() if value else value

    @field_validator("purchase_date")
    @classmethod
    def not_in_future(cls, value):
        if value and value > today_vn():
            raise ValueError("Ngày mua không được ở tương lai.")
        return value


class ArchiveIn(BaseModel):
    archived: bool = True


class VehicleOut(BaseModel):
    """A vehicle plus what its list card and detail header show."""

    id: int
    name: str
    vehicle_type: VehicleType
    brand: str | None
    model: str | None
    manufacture_year: int | None
    license_plate: str | None
    current_odometer: int
    purchase_date: date | None
    is_archived: bool
    created_at: datetime
    record_count: int
    last_service_date: date | None
    total_cost: Decimal
    overdue_count: int
    due_soon_count: int


# ---------- M3 Lần bảo dưỡng (Lâm) ----------


class ServiceTypeOut(BaseModel):
    id: int
    name: str
    description: str | None
    applies_to: str  # MOTORBIKE | CAR | ALL
    default_interval_km: int | None
    default_interval_months: int | None
    is_active: bool
    used_count: int = 0
    is_builtin: bool = False  # a default type: everyone sees it, nobody edits it


class AppliesTo(str, Enum):
    MOTORBIKE = "MOTORBIKE"
    CAR = "CAR"
    ALL = "ALL"


class ServiceTypeIn(BaseModel):
    """FR-12. Only the name is required; an empty interval means "no default" (NULL)."""

    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    description: Annotated[str, StringConstraints(max_length=255)] | None = None
    applies_to: AppliesTo = AppliesTo.ALL
    default_interval_km: Annotated[int, Field(gt=0, le=1_000_000)] | None = None
    default_interval_months: Annotated[int, Field(gt=0, le=240)] | None = None

    @field_validator("description", mode="before")
    @classmethod
    def empty_is_none(cls, value):
        return blank_to_none(value)


class ActiveIn(BaseModel):
    active: bool = True


class ItemIn(BaseModel):
    service_type_id: Annotated[int, Field(gt=0)]
    description: Annotated[str, StringConstraints(max_length=255)] | None = None
    quantity: Annotated[Decimal, Field(gt=0, max_digits=8, decimal_places=2)] = Decimal(1)
    unit_price: Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=0)] = Decimal(0)

    @field_validator("description", mode="before")
    @classmethod
    def empty_is_none(cls, value):
        return blank_to_none(value)

    @model_validator(mode="after")
    def line_total_fits(self):
        # maintenance_items.line_total is numeric(14,0): a bigger product would fail in the database (500)
        if self.quantity * self.unit_price >= Decimal(10) ** 14:
            raise ValueError("Thành tiền quá lớn, hãy kiểm tra số lượng và đơn giá.")
        return self


class RecordIn(BaseModel):
    """FR-06, FR-09. BR-03: not in the future. BR-04: at least one item."""

    service_date: date
    odometer: Annotated[int, Field(ge=0, le=10_000_000)]
    garage_name: Annotated[str, StringConstraints(max_length=100)] | None = None
    note: Annotated[str, StringConstraints(max_length=500)] | None = None
    items: Annotated[list[ItemIn], Field(min_length=1, max_length=30)]

    @field_validator("garage_name", "note", mode="before")
    @classmethod
    def empty_is_none(cls, value):
        return blank_to_none(value)

    @field_validator("service_date")
    @classmethod
    def not_in_future(cls, value):
        if value > today_vn():
            raise ValueError("Ngày bảo dưỡng không được ở tương lai.")
        return value


class ItemOut(BaseModel):
    id: int
    service_type_id: int
    service_type_name: str
    description: str | None
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal  # computed by the database (BR-05)


class RecordListItem(RecordSummary):
    """A row of a vehicle's history: RecordSummary plus the service types done."""

    note: str | None
    items_summary: str | None


class RecordOut(RecordSummary):
    vehicle_id: int
    vehicle_name: str
    license_plate: str | None
    note: str | None
    items: list[ItemOut]


# ---------- M6 Chi phí (Khoa) ----------


class CostMonth(BaseModel):
    month: int  # 1..12
    total: Decimal


class CostByType(BaseModel):
    service_type_id: int
    service_type_name: str
    total: Decimal


class CostByVehicle(BaseModel):
    vehicle_id: int
    vehicle_name: str
    vehicle_type: VehicleType
    license_plate: str | None
    record_count: int
    total: Decimal


class CostsOut(BaseModel):
    """FR-17. year None = all time; vehicle_id None = all vehicles."""

    year: int | None
    vehicle_id: int | None
    total: Decimal
    record_count: int
    item_count: int
    months: list[CostMonth]  # always 12 entries; for all time, the same month of every year is added up
    by_service_type: list[CostByType]
    by_vehicle: list[CostByVehicle]

# ---------- M5 Nhắc lịch (Lâm) ----------


class ReminderIn(BaseModel):
    """FR-13. BR-06: at least one interval. start_date and start_odometer are the first base mark (BR-07):
    left out, the latest record of the same service type is used, else today and the vehicle's odometer."""

    service_type_id: Annotated[int, Field(gt=0)]
    interval_km: Annotated[int, Field(gt=0, le=1_000_000)] | None = None
    interval_months: Annotated[int, Field(gt=0, le=240)] | None = None
    notify_before_days: Annotated[int, Field(ge=0, le=365)] = 7
    notify_before_km: Annotated[int, Field(ge=0, le=100_000)] = 300
    start_date: date | None = None
    start_odometer: Annotated[int, Field(ge=0, le=10_000_000)] | None = None

    @model_validator(mode="after")
    def has_an_interval(self):
        if self.interval_km is None and self.interval_months is None:
            raise ValueError("Cần nhập chu kỳ theo km hoặc theo tháng.")
        return self

    @field_validator("start_date")
    @classmethod
    def start_not_in_future(cls, value):
        if value and value > today_vn():
            raise ValueError("Ngày bắt đầu không được ở tương lai.")
        return value


class ReminderDetailOut(ReminderOut):
    """A reminder as its card and its edit form need it."""

    current_odometer: int
    notify_before_days: int
    notify_before_km: int
    start_date: date
    start_odometer: int
    progress: float  # 0..1 share of the interval already used, the larger of time and distance
