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


# Vehicles (M2, Lâm). {vehicle_id:int}: "/xe/moi" is the add form, never a vehicle id.
@router.get("/xe")
def vehicles_page(request: Request):
    return templates.TemplateResponse(request, "vehicles.html", {"active": "xe"})


@router.get("/xe/moi")
def vehicle_add_page(request: Request):
    return templates.TemplateResponse(request, "vehicle_form.html", {"active": "xe", "vehicle_id": None})


@router.get("/xe/{vehicle_id:int}")
def vehicle_detail_page(request: Request, vehicle_id: int):
    return templates.TemplateResponse(request, "vehicle_detail.html", {"active": "xe", "vehicle_id": vehicle_id})


@router.get("/xe/{vehicle_id:int}/sua")
def vehicle_edit_page(request: Request, vehicle_id: int):
    return templates.TemplateResponse(request, "vehicle_form.html", {"active": "xe", "vehicle_id": vehicle_id})


# Maintenance records (M3, Lâm). "/bao-duong/moi?xe=<id>&loai=<service type id>" preselects both.
@router.get("/bao-duong/moi")
def record_add_page(request: Request):
    return templates.TemplateResponse(request, "record_form.html", {"active": "xe", "record_id": None})


@router.get("/bao-duong/{record_id:int}")
def record_detail_page(request: Request, record_id: int):
    return templates.TemplateResponse(request, "record_detail.html", {"active": "xe", "record_id": record_id})


@router.get("/bao-duong/{record_id:int}/sua")
def record_edit_page(request: Request, record_id: int):
    return templates.TemplateResponse(request, "record_form.html", {"active": "xe", "record_id": record_id})


# Screens built by teammates (docs/PHAN-CONG.md §2.1). Until then the link opens a page that says who
# Service types (M4, Khoa)
@router.get("/loai-dich-vu")
def service_types_page(request: Request):
    return templates.TemplateResponse(request, "service_types.html", {"active": "loai-dich-vu"})
# builds it, so links from the home screen never end on a 404.
# path -> (menu key, title, screen in ui-design.html, owner)
UPCOMING = {
    "/thong-ke": ("thong-ke", "Chi phí", "Chi phí", "Khoa"),
   
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
