from contextlib import contextmanager

import psycopg
from fastapi.testclient import TestClient
from psycopg_pool import PoolTimeout

from app import db
from app.errors import ApiError
from app.main import APP_VERSION, app

client = TestClient(app)


class FakeConnection:
    def __init__(self, count):
        self.count = count

    def execute(self, query):
        assert "vehicles" in query
        return self

    def fetchone(self):
        return (self.count,)


def fake_pool_connection(count):
    @contextmanager
    def connection(timeout=None):
        yield FakeConnection(count)

    return connection


def broken_pool_connection(timeout=None):
    raise psycopg.OperationalError("connection refused")


def timed_out_pool_connection(timeout=None):
    raise PoolTimeout("couldn't get a connection after 5.00 sec")


def test_info():
    r = client.get("/api/info")
    assert r.status_code == 200
    body = r.json()
    assert body["app"] == "vehicle-maintenance-log"
    assert body["version"] == APP_VERSION


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_health_does_not_touch_database(monkeypatch):
    monkeypatch.setattr(db.pool, "connection", broken_pool_connection)
    r = client.get("/health")
    assert r.status_code == 200


def test_health_db_ok(monkeypatch):
    monkeypatch.setattr(db.pool, "connection", fake_pool_connection(3))
    r = client.get("/health/db")
    assert r.status_code == 200
    assert r.json() == {"db": "ok", "vehicles": 3}


def test_health_db_returns_503_when_database_is_down(monkeypatch):
    monkeypatch.setattr(db.pool, "connection", broken_pool_connection)
    r = client.get("/health/db")
    assert r.status_code == 503
    assert r.json() == {"db": "error"}


def test_health_db_returns_503_when_pool_times_out(monkeypatch):
    monkeypatch.setattr(db.pool, "connection", timed_out_pool_connection)
    r = client.get("/health/db")
    assert r.status_code == 503
    assert r.json() == {"db": "error"}


def test_api_error_becomes_error_out():
    @app.get("/_test/api-error")
    def raise_api_error():
        raise ApiError(409, "DUPLICATE_PLATE", "Biển số đã tồn tại.")

    r = client.get("/_test/api-error")
    assert r.status_code == 409
    assert r.json() == {"error_code": "DUPLICATE_PLATE", "message": "Biển số đã tồn tại."}
