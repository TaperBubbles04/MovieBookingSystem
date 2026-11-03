from pydantic import BaseModel
from typing import Optional, Any


class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None
    extra: Optional[dict] = None


class PaginationParams(BaseModel):
    limit: int = 20
    offset: int = 0


class PaginatedResponse(BaseModel):
    total: int
    limit: int
    offset: int


class HealthResponse(BaseModel):
    status: str
    service: str
