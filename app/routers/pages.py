"""HTML pages (doc 07: router pages). Each page is a Jinja2 shell; app.js loads the data from /api/*."""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent / "templates")

router = APIRouter(include_in_schema=False)


@router.get("/")
def dashboard(request: Request):
    return templates.TemplateResponse(request, "dashboard.html", {"active": "dashboard"})


@router.get("/chan-doan")
def diagnose_page(request: Request):
    return templates.TemplateResponse(request, "diagnose.html", {"active": "chan-doan"})


@router.get("/chan-doan/lich-su")
def diagnosis_history_page(request: Request):
    return templates.TemplateResponse(request, "ai_history.html", {"active": "lich-su-ai"})


# Screens built by teammates (docs/PHAN-CONG.md §2.1). Until then the link opens a page that says who
# builds it, so links from the home screen never end on a 404.
# path -> (menu key, title, screen in ui-design.html, owner)
UPCOMING = {
    "/xe": ("xe", "Xe của tôi", "Xe của tôi", "Lâm"),
    "/xe/{vehicle_id}": ("xe", "Chi tiết xe", "Chi tiết xe", "Lâm"),
    "/bao-duong/moi": ("xe", "Ghi lần bảo dưỡng", "Ghi lần bảo dưỡng", "Lâm"),
    "/bao-duong/{record_id}": ("xe", "Chi tiết lần bảo dưỡng", "Chi tiết lần bảo dưỡng", "Lâm"),
    "/thong-ke": ("thong-ke", "Chi phí", "Chi phí", "Khoa"),
    "/loai-dich-vu": ("loai-dich-vu", "Loại việc bảo dưỡng", "Loại việc bảo dưỡng", "Khoa"),
    "/them": ("them", "Thêm", "Thêm", "Khoa"),
}


def upcoming_page(path: str):
    active, title, screen, owner = UPCOMING[path]

    def page(request: Request):
        context = {"active": active, "title": title, "screen": screen, "owner": owner}
        return templates.TemplateResponse(request, "upcoming.html", context)

    return page


for _path in UPCOMING:
    router.add_api_route(_path, upcoming_page(_path), methods=["GET"])
