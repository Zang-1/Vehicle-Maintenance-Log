"""Vehicle Maintenance Log — 72ITDS30103 Software Development Platforms."""

import os
from contextlib import asynccontextmanager

import psycopg
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app import db
from app.errors import ApiError
from app.schemas import ErrorOut, HealthDbOut, HealthOut, RootOut

APP_NAME = os.getenv("APP_NAME", "vehicle-maintenance-log")
APP_VERSION = "0.1.0"  # bump in a pull request to trace a commit to production
APP_ENV = os.getenv("APP_ENV", "development")


@asynccontextmanager
async def lifespan(app):
    db.open_pool()
    yield
    db.close_pool()


app = FastAPI(title=APP_NAME, version=APP_VERSION, lifespan=lifespan)


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, err: ApiError):
    body = ErrorOut(error_code=err.error_code, message=err.message)
    return JSONResponse(status_code=err.status_code, content=body.model_dump())


@app.get("/", response_model=RootOut)
def root():
    return RootOut(app=APP_NAME, version=APP_VERSION, env=APP_ENV, message="Vehicle Maintenance Log API")


@app.get("/health", response_model=HealthOut)
def health():
    # Fast, no login, touches nothing. Render's health check path points here.
    return HealthOut(status="ok")


@app.get(
    "/health/db",
    response_model=HealthDbOut,
    responses={503: {"description": "Database unreachable", "content": {"application/json": {"example": {"db": "error"}}}}},
)
def health_db():
    # Proves the database works. Borrows a connection from the pool for one query.
    try:
        with db.pool.connection(timeout=5) as conn:
            n = conn.execute("SELECT count(*) FROM vehicles").fetchone()[0]
        return HealthDbOut(db="ok", vehicles=n)
    except psycopg.Error as err:  # includes PoolTimeout: database paused or unreachable
        print("health/db failed:", type(err).__name__, err, flush=True)  # details to the logs only
        return JSONResponse(status_code=503, content={"db": "error"})
