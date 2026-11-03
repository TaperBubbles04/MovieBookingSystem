from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, time, datetime


class ShowBase(BaseModel):
    movie_id: int
    screen_id: int
    show_date: date
    start_time: time
    end_time: time


class ShowCreate(ShowBase):
    pass


class ShowPricingItem(BaseModel):
    seat_category: str = Field(..., pattern="^(REGULAR|PREMIUM|RECLINER)$")
    price: int = Field(..., ge=0)


class ShowPricingUpdate(BaseModel):
    pricing: List[ShowPricingItem]


class ShowPricingResponse(BaseModel):
    seat_category: str
    price: int


class MovieBasic(BaseModel):
    movie_id: int
    title: str
    duration_min: int
    poster_url: Optional[str] = None

    class Config:
        from_attributes = True


class TheatreBasic(BaseModel):
    theatre_id: int
    name: str
    city: str

    class Config:
        from_attributes = True


class ScreenBasic(BaseModel):
    screen_id: int
    screen_name: str
    screen_type: str

    class Config:
        from_attributes = True


class ShowResponse(ShowBase):
    show_id: int
    movie: MovieBasic
    theatre: TheatreBasic
    screen: ScreenBasic
    pricing: List[ShowPricingResponse] = []

    class Config:
        from_attributes = True


class ShowListResponse(BaseModel):
    shows: List[ShowResponse]
    total: int


class SeatMapItem(BaseModel):
    seat_id: int
    row_label: str
    seat_number: int
    seat_category: str
    price: int
    status: str  # "available" or "taken"


class SeatMapResponse(BaseModel):
    show_id: int
    screen: ScreenBasic
    seats: List[SeatMapItem]
    summary: dict  # {"total": int, "available": int, "taken": int}
