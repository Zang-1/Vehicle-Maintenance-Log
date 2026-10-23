"""Pydantic models (doc 07, sections 6.1 and 6.2).

M0 only holds the shared models. Each module adds its own models here
(VehicleIn/Out for M2, RecordIn for M3, ...) in its own pull request.
"""

from pydantic import BaseModel


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
