"""AI diagnosis (M7, FR-18 → FR-20). The browser calls only POST /diagnose; app/ai.py calls Gemini."""

from fastapi import APIRouter

from app import ai
from app.errors import ApiError
from app.schemas import DiagnoseIn, DiagnoseOut, ErrorOut

router = APIRouter(tags=["ai"])

FRIENDLY = "Tính năng chẩn đoán AI tạm thời không khả dụng, vui lòng thử lại sau ít phút."


@router.post("/diagnose", response_model=DiagnoseOut, responses={503: {"model": ErrorOut}})
def diagnose(req: DiagnoseIn):
    try:
        suggestion = ai.summarize_safe(req.symptom_text)
    except ai.AIUnavailable as err:
        print("ai failed:", err.reason, flush=True)  # the reason goes to the logs, never the key
        raise ApiError(503, "AI_UNAVAILABLE", FRIENDLY) from err
    return DiagnoseOut(suggestion=suggestion)
