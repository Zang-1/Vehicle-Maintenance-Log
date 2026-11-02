from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import app
from tests.fakedb import use_fake_db

client = TestClient(app)


def script():
    return [
        ("AS grand_total", {"grand_total": Decimal(500000), "record_count": 2, "item_count": 3}),
        ("AS month", [{"month": 3, "total": Decimal(200000)}, {"month": 8, "total": Decimal(300000)}]),
        ("GROUP BY st.id", [{"service_type_id": 1, "service_type_name": "Thay nhớt", "total": Decimal(300000)}]),
        ("GROUP BY v.id", [{
            "vehicle_id": 1, "vehicle_name": "Vision", "vehicle_type": "MOTORBIKE",
            "license_plate": "59X1-123.45", "record_count": 2, "total": Decimal(500000),
        }]),
    ]


def test_costs_fills_all_twelve_months(monkeypatch):
    cursor = use_fake_db(monkeypatch, script())
    response = client.get("/api/stats/costs?year=2026")
    assert response.status_code == 200
    body = response.json()
    assert Decimal(body["total"]) == 500000
    assert body["record_count"] == 2
    assert body["item_count"] == 3
    assert [m["month"] for m in body["months"]] == list(range(1, 13))
    assert Decimal(body["months"][2]["total"]) == 200000  # March
    assert Decimal(body["months"][0]["total"]) == 0  # January has no record
    assert body["by_service_type"][0]["service_type_name"] == "Thay nhớt"
    assert body["by_vehicle"][0]["vehicle_name"] == "Vision"
    assert cursor.calls[0][1] == {"year": 2026, "vehicle_id": None}


def test_costs_without_year_means_all_time(monkeypatch):
    cursor = use_fake_db(monkeypatch, script())
    body = client.get("/api/stats/costs").json()
    assert body["year"] is None
    assert cursor.calls[0][1] == {"year": None, "vehicle_id": None}


def test_costs_filters_by_vehicle(monkeypatch):
    cursor = use_fake_db(monkeypatch, script())
    assert client.get("/api/stats/costs?year=2026&vehicle_id=1").status_code == 200
    assert cursor.calls[0][1] == {"year": 2026, "vehicle_id": 1}


def test_costs_with_no_records(monkeypatch):
    use_fake_db(monkeypatch, [("AS grand_total", {"grand_total": Decimal(0), "record_count": 0, "item_count": 0})])
    body = client.get("/api/stats/costs").json()
    assert body["record_count"] == 0
    assert len(body["months"]) == 12
    assert body["by_service_type"] == []
    assert body["by_vehicle"] == []


def test_costs_rejects_a_silly_year(monkeypatch):
    use_fake_db(monkeypatch, [])
    assert client.get("/api/stats/costs?year=1999").status_code == 422

def test_costs_page_is_real():
    response = client.get("/thong-ke")
    assert response.status_code == 200
    assert "đang được xây dựng" not in response.text
    assert 'id="cost-body"' in response.text