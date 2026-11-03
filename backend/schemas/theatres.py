from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class TheatreBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    city: str = Field(..., min_length=1, max_length=50)
    address: str = Field(..., min_length=1)


class TheatreCreate(TheatreBase):
    pass


class TheatreResponse(TheatreBase):
    theatre_id: int

    class Config:
        from_attributes = True


class ScreenBase(BaseModel):
    screen_name: str = Field(..., min_length=1)
    screen_type: str = Field(..., pattern="^(2D|3D|IMAX)$")


class ScreenCreate(ScreenBase):
    rows: str = Field(..., description="Comma-separated row labels, e.g., 'A,B,C,D,E,F,G,H'")
    seats_per_row: int = Field(..., gt=0)
    premium_rows: Optional[str] = Field(default=None, description="Comma-separated row labels for PREMIUM")
    recliner_rows: Optional[str] = Field(default=None, description="Comma-separated row labels for RECLINER")


class ScreenResponse(ScreenBase):
    screen_id: int
    theatre_id: int

    class Config:
        from_attributes = True


class ScreenCreateResponse(BaseModel):
    screen_id: int
    theatre_id: int
    screen_name: str
    screen_type: str
    seats_created: int
    seat_layout: dict
