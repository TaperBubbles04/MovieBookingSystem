"""JSON API for CineBook, served under /api.

The web pages in main.py return HTML and keep the login in a session cookie.
These routes return JSON and take a Bearer token instead, so scripts and tools
such as Swytchcode can call them. Booking and cancelling reuse the same
transactions as the web pages (services/booking_service.py and
services/cancellation_service.py).

Errors always have the shape {"detail": "...", "code": "..."}, as described
in docs/api_contract.md.
"""
from datetime import date, datetime, time, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Header, Query

from auth import create_token, decode_token, verify_password
from database import get_db
from schemas.auth import LoginRequest
from schemas.bookings import BookingCreate
from services.booking_service import create_booking
from services.cancellation_service import cancel_booking

router = APIRouter(prefix="/api", tags=["api"])

MAX_SEATS_PER_BOOKING = 6
CANCEL_CUTOFF = timedelta(hours=2)


class ApiError(Exception):
    """An error sent to the client as {"detail": ..., "code": ...}."""

    def __init__(self, status_code: int, detail: str, code: str):
        self.status_code = status_code
        self.detail = detail
        self.code = code


# The booking and cancellation services raise ValueError with a message.
# Match the start of each message to an HTTP status and an error code.
SERVICE_ERRORS = [
    ("Show not found", 404, "NOT_FOUND"),
    ("Booking not found", 404, "NOT_FOUND"),
    ("Show has already started", 400, "SHOW_STARTED"),
    ("One or more seats", 400, "INVALID_SEATS"),
    ("Seat(s)", 409, "SEAT_TAKEN"),
    ("Not authorized", 403, "FORBIDDEN"),
    ("Only confirmed", 400, "NOT_CONFIRMED"),
    ("Cannot cancel", 409, "TOO_LATE"),
]


def service_error(message: str) -> ApiError:
    for prefix, status_code, code in SERVICE_ERRORS:
        if message.startswith(prefix):
            return ApiError(status_code, message, code)
    return ApiError(400, message, "BAD_REQUEST")


def iso(value):
    """Dates as YYYY-MM-DD, times as HH:MM, timestamps as ISO 8601."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, time):
        return value.strftime("%H:%M")
    return value


# ===== AUTH =====

USER_COLUMNS = "customer_id, name, email, phone, role, created_at"


def user_json(row) -> dict:
    return {
        "customer_id": row[0], "name": row[1], "email": row[2],
        "phone": row[3], "role": row[4], "created_at": iso(row[5]),
    }


def current_user(authorization: Optional[str] = Header(None)) -> dict:
    """Reads 'Authorization: Bearer <token>' and loads that customer."""
    if not authorization or not authorization.startswith("Bearer "):
        raise ApiError(401, "Log in first and send 'Authorization: Bearer <token>'", "UNAUTHORIZED")

    payload = decode_token(authorization[len("Bearer "):].strip())
    customer_id = str((payload or {}).get("sub", ""))
    if not customer_id.isdigit():
        raise ApiError(401, "Invalid or expired token", "UNAUTHORIZED")

    with get_db() as cur:
        cur.execute(f"SELECT {USER_COLUMNS} FROM Customer WHERE customer_id = %s", (int(customer_id),))
        row = cur.fetchone()
    if not row:
        raise ApiError(401, "Invalid or expired token", "UNAUTHORIZED")
    return user_json(row)


@router.get("/health")
def health():
    """Checks that the API is up and can reach the database."""
    try:
        with get_db() as cur:
            cur.execute("SELECT 1")
    except Exception:
        raise ApiError(503, "Database unreachable", "DB_UNAVAILABLE")
    return {"status": "ok", "database": "ok"}


@router.post("/auth/login")
def login(body: LoginRequest):
    with get_db() as cur:
        cur.execute(f"SELECT {USER_COLUMNS}, password_hash FROM Customer WHERE email = %s", (body.email,))
        row = cur.fetchone()

    if not row or not verify_password(body.password, row[6]):
        raise ApiError(401, "Invalid email or password", "INVALID_CREDENTIALS")

    token = create_token({"sub": str(row[0]), "role": row[4]})
    return {"user": user_json(row), "token": token, "token_type": "bearer"}


@router.get("/auth/me")
def me(user: dict = Depends(current_user)):
    return user


# ===== MOVIES =====

MOVIE_COLUMNS = """
    m.movie_id, m.title, m.description, m.duration_min, m.language,
    m.certificate, m.release_date, m.rating, m.poster_url,
    COALESCE((SELECT ARRAY_AGG(g.genre_name ORDER BY g.genre_name)
              FROM Movie_Genre mg JOIN Genre g ON g.genre_id = mg.genre_id
              WHERE mg.movie_id = m.movie_id), '{}') AS genres
"""


def movie_json(row) -> dict:
    return {
        "movie_id": row[0], "title": row[1], "description": row[2],
        "duration_min": row[3], "language": row[4], "certificate": row[5],
        "release_date": iso(row[6]),
        "rating": float(row[7]) if row[7] is not None else None,
        "poster_url": row[8], "genres": list(row[9]),
    }


@router.get("/movies")
def list_movies(
    search: str = "",
    genre: str = "",
    language: str = "",
    certificate: str = "",
    min_rating: float = Query(0, ge=0, le=10),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    where, params = ["TRUE"], []
    if search:
        where.append("m.title ILIKE %s")
        params.append(f"%{search}%")
    if genre:
        # Filter with EXISTS so each movie still lists all of its genres
        where.append("""EXISTS (SELECT 1 FROM Movie_Genre mg JOIN Genre g ON g.genre_id = mg.genre_id
                                WHERE mg.movie_id = m.movie_id AND g.genre_name ILIKE %s)""")
        params.append(genre)
    if language:
        where.append("m.language ILIKE %s")
        params.append(language)
    if certificate:
        where.append("m.certificate = %s")
        params.append(certificate.upper())
    if min_rating > 0:
        where.append("m.rating >= %s")
        params.append(min_rating)
    where_sql = " AND ".join(where)

    with get_db() as cur:
        cur.execute(f"SELECT COUNT(*) FROM Movie m WHERE {where_sql}", params)
        total = cur.fetchone()[0]
        cur.execute(f"""
            SELECT {MOVIE_COLUMNS} FROM Movie m WHERE {where_sql}
            ORDER BY m.title LIMIT %s OFFSET %s
        """, params + [limit, offset])
        rows = cur.fetchall()

    return {"movies": [movie_json(r) for r in rows], "total": total, "limit": limit, "offset": offset}


@router.get("/movies/{movie_id}")
def get_movie(movie_id: int):
    with get_db() as cur:
        cur.execute(f"SELECT {MOVIE_COLUMNS} FROM Movie m WHERE m.movie_id = %s", (movie_id,))
        row = cur.fetchone()
    if not row:
        raise ApiError(404, "Movie not found", "NOT_FOUND")
    return movie_json(row)


# ===== SHOWS AND SEATS =====

SHOW_COLUMNS = """
    s.show_id, s.show_date, s.start_time, s.end_time,
    m.movie_id, m.title, m.duration_min, m.poster_url,
    t.theatre_id, t.name, t.city,
    sc.screen_id, sc.screen_name, sc.screen_type,
    (SELECT COUNT(*) FROM Seat WHERE screen_id = sc.screen_id)
      - (SELECT COUNT(*) FROM Ticket WHERE show_id = s.show_id AND status = 'ACTIVE') AS seats_left
"""
SHOW_JOINS = """
    FROM "show" s
    JOIN Movie m ON m.movie_id = s.movie_id
    JOIN Screen sc ON sc.screen_id = s.screen_id
    JOIN Theatre t ON t.theatre_id = sc.theatre_id
"""


def show_json(row) -> dict:
    return {
        "show_id": row[0], "show_date": iso(row[1]),
        "start_time": iso(row[2]), "end_time": iso(row[3]),
        "movie": {"movie_id": row[4], "title": row[5], "duration_min": row[6], "poster_url": row[7]},
        "theatre": {"theatre_id": row[8], "name": row[9], "city": row[10]},
        "screen": {"screen_id": row[11], "screen_name": row[12], "screen_type": row[13]},
        "seats_left": row[14],
    }


@router.get("/shows")
def list_shows(
    movie_id: Optional[int] = None,
    show_date: Optional[date] = Query(None, alias="date"),
    city: str = "",
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Lists shows that have not started yet, soonest first."""
    # Compare with Python's clock, the same one the booking service uses
    where, params = ["(s.show_date + s.start_time) > %s"], [datetime.now()]
    if movie_id is not None:
        where.append("s.movie_id = %s")
        params.append(movie_id)
    if show_date is not None:
        where.append("s.show_date = %s")
        params.append(show_date)
    if city:
        where.append("t.city ILIKE %s")
        params.append(city)
    where_sql = " AND ".join(where)

    with get_db() as cur:
        cur.execute(f"SELECT COUNT(*) {SHOW_JOINS} WHERE {where_sql}", params)
        total = cur.fetchone()[0]
        cur.execute(f"""
            SELECT {SHOW_COLUMNS} {SHOW_JOINS} WHERE {where_sql}
            ORDER BY s.show_date, s.start_time, t.name LIMIT %s OFFSET %s
        """, params + [limit, offset])
        rows = cur.fetchall()

    return {"shows": [show_json(r) for r in rows], "total": total, "limit": limit, "offset": offset}


@router.get("/shows/{show_id}/seats")
def show_seats(show_id: int):
    """The seat map for one show: each seat's category, price and status."""
    with get_db() as cur:
        cur.execute(f"SELECT {SHOW_COLUMNS} {SHOW_JOINS} WHERE s.show_id = %s", (show_id,))
        show = cur.fetchone()
        if not show:
            raise ApiError(404, "Show not found", "NOT_FOUND")

        cur.execute("""
            SELECT st.seat_id, st.row_label, st.seat_number, st.seat_category, sp.price,
                   CASE WHEN tk.ticket_id IS NULL THEN 'available' ELSE 'taken' END
            FROM Seat st
            JOIN Show_Pricing sp ON sp.show_id = %s AND sp.seat_category = st.seat_category
            LEFT JOIN Ticket tk ON tk.show_id = %s AND tk.seat_id = st.seat_id AND tk.status = 'ACTIVE'
            WHERE st.screen_id = %s
            ORDER BY st.row_label, st.seat_number
        """, (show_id, show_id, show[11]))
        rows = cur.fetchall()

    seats = [{
        "seat_id": r[0], "label": f"{r[1]}-{r[2]}", "row_label": r[1], "seat_number": r[2],
        "seat_category": r[3], "price": r[4], "status": r[5],
    } for r in rows]
    taken = sum(1 for s in seats if s["status"] == "taken")

    return {
        "show": show_json(show),
        "seats": seats,
        "summary": {"total": len(seats), "available": len(seats) - taken, "taken": taken},
    }


# ===== BOOKINGS =====

def load_booking(cur, booking_id: int, user: dict) -> dict:
    """One booking with its show, tickets and payment. Owner or admin only."""
    cur.execute(f"""
        SELECT b.booking_id, b.customer_id, b.booking_time, b.total_amount, b.status,
               {SHOW_COLUMNS}
        FROM Booking b
        JOIN "show" s ON s.show_id = b.show_id
        JOIN Movie m ON m.movie_id = s.movie_id
        JOIN Screen sc ON sc.screen_id = s.screen_id
        JOIN Theatre t ON t.theatre_id = sc.theatre_id
        WHERE b.booking_id = %s
    """, (booking_id,))
    row = cur.fetchone()
    if not row:
        raise ApiError(404, "Booking not found", "NOT_FOUND")
    if row[1] != user["customer_id"] and user["role"] != "ADMIN":
        raise ApiError(403, "This booking belongs to another customer", "FORBIDDEN")

    cur.execute("""
        SELECT tk.ticket_id, tk.seat_id, st.row_label, st.seat_number, st.seat_category, tk.price, tk.status
        FROM Ticket tk JOIN Seat st ON st.seat_id = tk.seat_id
        WHERE tk.booking_id = %s
        ORDER BY st.row_label, st.seat_number
    """, (booking_id,))
    tickets = [{
        "ticket_id": t[0], "seat_id": t[1], "seat": f"{t[2]}-{t[3]}",
        "seat_category": t[4], "price": t[5], "status": t[6],
    } for t in cur.fetchall()]

    cur.execute("SELECT payment_id, amount, method, status, paid_at FROM Payment WHERE booking_id = %s",
                (booking_id,))
    p = cur.fetchone()
    payment = {"payment_id": p[0], "amount": p[1], "method": p[2], "status": p[3],
               "paid_at": iso(p[4])} if p else None

    show = show_json(row[5:])
    status = row[4]
    starts_at = datetime.combine(row[6], row[7])  # show_date, start_time
    return {
        "booking_id": row[0],
        "customer_id": row[1],
        "booking_time": iso(row[2]),
        "total_amount": row[3],
        "status": status,
        "can_cancel": status == "CONFIRMED" and starts_at > datetime.now() + CANCEL_CUTOFF,
        "show": show,
        "tickets": tickets,
        "payment": payment,
    }


@router.post("/bookings", status_code=201)
def book(body: BookingCreate, user: dict = Depends(current_user)):
    """Books seats for a show and pays in one transaction."""
    if len(body.seat_ids) > MAX_SEATS_PER_BOOKING:
        raise ApiError(400, f"You can book at most {MAX_SEATS_PER_BOOKING} seats at a time", "TOO_MANY_SEATS")
    if len(set(body.seat_ids)) != len(body.seat_ids):
        raise ApiError(400, "The same seat is listed more than once", "DUPLICATE_SEATS")

    try:
        # The connection commits when this block ends, or rolls back on an error
        with get_db() as cur:
            result = create_booking(cur, user["customer_id"], body.show_id, body.seat_ids, body.payment_method)
    except ValueError as e:
        raise service_error(str(e))

    with get_db() as cur:
        return load_booking(cur, result["booking_id"], user)


@router.get("/bookings/me")
def my_bookings(
    user: dict = Depends(current_user),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """The logged-in customer's bookings, newest first."""
    with get_db() as cur:
        cur.execute("SELECT COUNT(*) FROM Booking WHERE customer_id = %s", (user["customer_id"],))
        total = cur.fetchone()[0]
        cur.execute("""
            SELECT b.booking_id, b.booking_time, b.total_amount, b.status,
                   s.show_id, s.show_date, s.start_time, m.title, t.name, sc.screen_name,
                   ARRAY_AGG(st.row_label || '-' || st.seat_number ORDER BY st.row_label, st.seat_number)
            FROM Booking b
            JOIN "show" s ON s.show_id = b.show_id
            JOIN Movie m ON m.movie_id = s.movie_id
            JOIN Screen sc ON sc.screen_id = s.screen_id
            JOIN Theatre t ON t.theatre_id = sc.theatre_id
            JOIN Ticket tk ON tk.booking_id = b.booking_id
            JOIN Seat st ON st.seat_id = tk.seat_id
            WHERE b.customer_id = %s
            GROUP BY b.booking_id, s.show_id, m.title, t.name, sc.screen_name
            ORDER BY b.booking_time DESC
            LIMIT %s OFFSET %s
        """, (user["customer_id"], limit, offset))
        rows = cur.fetchall()

    now = datetime.now()
    bookings = [{
        "booking_id": r[0], "booking_time": iso(r[1]), "total_amount": r[2], "status": r[3],
        "show_id": r[4], "show_date": iso(r[5]), "start_time": iso(r[6]),
        "movie": r[7], "theatre": r[8], "screen": r[9], "seats": list(r[10]),
        "can_cancel": r[3] == "CONFIRMED" and datetime.combine(r[5], r[6]) > now + CANCEL_CUTOFF,
    } for r in rows]
    return {"bookings": bookings, "total": total, "limit": limit, "offset": offset}


@router.get("/bookings/{booking_id}")
def get_booking(booking_id: int, user: dict = Depends(current_user)):
    with get_db() as cur:
        return load_booking(cur, booking_id, user)


@router.post("/bookings/{booking_id}/cancel")
def cancel(booking_id: int, user: dict = Depends(current_user)):
    """Cancels a booking and refunds it, up to 2 hours before the show."""
    try:
        with get_db() as cur:
            result = cancel_booking(cur, user["customer_id"], booking_id)
            cur.execute("SELECT COUNT(*) FROM Ticket WHERE booking_id = %s AND status = 'CANCELLED'",
                        (booking_id,))
            result["tickets_cancelled"] = cur.fetchone()[0]
    except ValueError as e:
        raise service_error(str(e))
    return result
