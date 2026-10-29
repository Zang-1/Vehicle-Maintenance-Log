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


# Menu entries whose screens come with later modules. Until then they show who builds them.
UPCOMING = {
    "xe": ("Xe của tôi", "S02–S07", "M2, M3 – Lâm"),
    "loai-dich-vu": ("Loại dịch vụ", "S09", "M4 – Khoa"),
    "thong-ke": ("Thống kê chi phí", "S08", "M6 – Khoa"),
}


def upcoming_page(slug: str):
    title, screens, owner = UPCOMING[slug]

    def page(request: Request):
        context = {"active": slug, "title": title, "screens": screens, "owner": owner}
        return templates.TemplateResponse(request, "upcoming.html", context)

    return page


for _slug in UPCOMING:
    router.add_api_route(f"/{_slug}", upcoming_page(_slug), methods=["GET"])
