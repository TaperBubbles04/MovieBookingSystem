from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class BookingCreate(BaseModel):
    show_id: int
    seat_ids: List[int] = Field(..., min_length=1)
    payment_method: str = Field(..., pattern="^(UPI|CARD|CASH)$")


class TicketResponse(BaseModel):
    ticket_id: int
    seat_id: int
    price: int
    status: str

    class Config:
        from_attributes = True


class PaymentResponse(BaseModel):
    payment_id: int
    amount: int
    method: str
    status: str
    paid_at: datetime

    class Config:
        from_attributes = True


class BookingResponse(BaseModel):
    booking_id: int
    customer_id: int
    show_id: int
    booking_time: datetime
    total_amount: int
    status: str

    class Config:
        from_attributes = True


class BookingCreateResponse(BaseModel):
    booking: BookingResponse
    tickets: List[TicketResponse]
    payment: PaymentResponse


class SeatLabelResponse(BaseModel):
    row_label: str
    seat_number: int


class BookingDetailResponse(BaseModel):
    booking: BookingResponse
    movie: "MovieBasic"
    theatre: "TheatreBasic"
    screen: "ScreenBasic"
    show_date: str
    start_time: str
    seats: List[SeatLabelResponse]
    tickets: List[TicketResponse]
    payment: PaymentResponse

    class Config:
        from_attributes = True


class MyBookingItem(BaseModel):
    booking_id: int
    show_id: int
    movie: "MovieBasic"
    theatre: "TheatreBasic"
    screen: "ScreenBasic"
    show_date: str
    start_time: str
    total_amount: int
    status: str
    seats: List[str]  # e.g., ["A-5", "A-6"]
    booking_time: datetime


class MyBookingsResponse(BaseModel):
    bookings: List[MyBookingItem]
    total: int


class CancelResponse(BaseModel):
    booking_id: int
    status: str
    tickets_cancelled: int
    refunded_amount: int
    payment_status: str


# Forward references - MovieBasic is in schemas.shows, TheatreBasic/ScreenBasic in schemas.theatres
from .shows import MovieBasic, TheatreBasic, ScreenBasic
