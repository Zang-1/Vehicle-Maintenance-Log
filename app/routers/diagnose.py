"""AI diagnosis (M7, FR-18 → FR-21). The browser calls only POST /diagnose; app/ai.py calls Gemini.

Every call is saved in the diagnoses table (FR-21), the failed ones too: they are the evidence
for the report's "AI integration" section.
"""

import re

import psycopg
from fastapi import APIRouter
from psycopg.rows import dict_row

from app import ai, db
from app.auth import CurrentUser
from app.errors import ApiError
from app.schemas import DiagnoseIn, DiagnoseOut, DiagnosisOut, ErrorOut

router = APIRouter(tags=["ai"])

FRIENDLY = "Tính năng chẩn đoán AI tạm thời không khả dụng, vui lòng thử lại sau ít phút."

# The prompt asks for a last line "Mức khẩn cấp: LOW|MEDIUM|HIGH".
URGENCY = re.compile(r"(?:mức khẩn cấp|urgency)\s*:\s*\**\s*(LOW|MEDIUM|HIGH)", re.IGNORECASE)

INSERT_SQL = """
INSERT INTO diagnoses (user_id, vehicle_id, symptom_text, status, ai_suggestion, urgency_level, error_code, model)
VALUES (%(user_id)s, %(vehicle_id)s, %(symptom_text)s, %(status)s, %(ai_suggestion)s, %(urgency_level)s, %(error_code)s, %(model)s)
"""  # FR-18: thêm vehicle_id

LIST_SQL = """
SELECT id, created_at, symptom_text, status, ai_suggestion, urgency_level, error_code, model
FROM diagnoses
WHERE user_id = %(uid)s
ORDER BY created_at DESC, id DESC
LIMIT 50
"""

# FR-18: chỉ lấy xe của người đang đăng nhập (FR-25)
VEHICLE_SQL = """
SELECT id, vehicle_type, brand, model, manufacture_year, current_odometer
FROM vehicles
WHERE id = %(vid)s AND user_id = %(uid)s
"""


def error_code(reason: str) -> str:
    """Map AIUnavailable.reason to the error codes allowed by the diagnoses table (BR-10)."""
    if "GEMINI_API_KEY" in reason:
        return "NO_KEY"
    if reason.startswith("HTTP 429"):
        return "RATE_LIMITED"
    if reason == "timeout":
        return "TIMEOUT"
    return "UPSTREAM_ERROR"


def load_vehicle(vehicle_id: int, user_id: int) -> dict:  # FR-18
    with db.pool.connection(timeout=5) as conn:
        row = conn.cursor(row_factory=dict_row).execute(
            VEHICLE_SQL, {"vid": vehicle_id, "uid": user_id}
        ).fetchone()
    if row is None:  # không tồn tại HOẶC của người khác: cùng một câu trả lời
        raise ApiError(404, "VEHICLE_NOT_FOUND", "Không tìm thấy xe.")
    return row


def save(row: dict) -> None:
    # A history row is nice to have; it must never cost the user the answer they waited for.
    try:
        with db.pool.connection(timeout=5) as conn:
            conn.execute(INSERT_SQL, row)
    except psycopg.Error as err:  # includes PoolTimeout
        print("diagnosis not saved:", type(err).__name__, err, flush=True)


@router.post(
    "/diagnose",
    response_model=DiagnoseOut,
    responses={404: {"model": ErrorOut}, 503: {"model": ErrorOut}},  # FR-18: thêm 404
)
def diagnose(req: DiagnoseIn, user: CurrentUser):
    # FR-18: kiểm tra xe TRƯỚC khi gọi AI, xe sai thì 404 và không tốn lượt gọi
    vehicle = load_vehicle(req.vehicle_id, user["id"]) if req.vehicle_id is not None else None
    row = {
        "user_id": user["id"],
        "vehicle_id": vehicle["id"] if vehicle else None,  # FR-18
        "symptom_text": req.symptom_text,
        "model": ai.AI_MODEL,
        "ai_suggestion": None,
        "urgency_level": None,
    }
    try:
        suggestion = ai.summarize_safe(req.symptom_text, vehicle_ctx=ai.describe_vehicle(vehicle))  # FR-18
    except ai.AIUnavailable as err:
        print("ai failed:", err.reason, flush=True)  # the reason goes to the logs, never the key
        save({**row, "status": "FAILED", "error_code": error_code(err.reason)})
        raise ApiError(503, "AI_UNAVAILABLE", FRIENDLY) from err
    match = URGENCY.search(suggestion)
    save({**row, "status": "OK", "error_code": None, "ai_suggestion": suggestion,
          "urgency_level": match.group(1).upper() if match else None})
    return DiagnoseOut(suggestion=suggestion)


@router.get("/api/diagnoses", response_model=list[DiagnosisOut])
def list_diagnoses(user: CurrentUser):
    with db.pool.connection(timeout=5) as conn:
        return conn.cursor(row_factory=dict_row).execute(LIST_SQL, {"uid": user["id"]}).fetchall()