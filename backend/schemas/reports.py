from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date


class RevenueByMovieItem(BaseModel):
    movie_id: int
    title: str
    total_revenue: int
    tickets_sold: int
    avg_price: int


class RevenueByMovieResponse(BaseModel):
    report: List[RevenueByMovieItem]


class OccupancyItem(BaseModel):
    show_id: int
    movie: str
    theatre: str
    screen: str
    show_date: date
    total_seats: int
    booked_seats: int
    occupancy_pct: float


class OccupancyResponse(BaseModel):
    report: List[OccupancyItem]


class TopCustomerItem(BaseModel):
    customer_id: int
    name: str
    email: str
    total_spent: int
    bookings_count: int


class TopCustomersResponse(BaseModel):
    report: List[TopCustomerItem]


class DailySalesItem(BaseModel):
    date: date
    revenue: int
    bookings: int


class DailySalesResponse(BaseModel):
    report: List[DailySalesItem]


class UnsoldMovieItem(BaseModel):
    movie_id: int
    title: str
    language: str
    certificate: str


class UnsoldMoviesResponse(BaseModel):
    report: List[UnsoldMovieItem]
