from fastapi import FastAPI, Request, Depends, Form, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(title="CineBook API", version="0.1.0")

# CORS for API (if frontend calls API directly)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:5173")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware for cookie-based auth (Jinja templates)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("JWT_SECRET", "your-super-secret-key-change-in-production"),
    max_age=1800,  # 30 minutes
)

# Flash message helper
def flash(request: Request, message: str, category: str = "info"):
    if "_flashes" not in request.session:
        request.session["_flashes"] = []
    request.session["_flashes"].append({"message": message, "category": category})

# Context processor to add flashes to all templates
def flash_context_processor(request: Request):
    if hasattr(request, 'session'):
        flashes = request.session.pop("_flashes", [])
    else:
        flashes = []
    return {"flashes": flashes}

# Templates and static files
templates = Jinja2Templates(
    directory="app/templates",
    context_processors=[flash_context_processor]
)
# Ensure static directory exists (fixes startup crash on fresh clone)
os.makedirs("app/static", exist_ok=True)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


# ===== DATABASE & AUTH SETUP (import after app creation to avoid circular) =====
from database import get_db
from auth import hash_password, verify_password, create_token, decode_token, get_current_user_from_cookie

# Dependency to get current user from session cookie
async def get_current_user(request: Request):
    """Get current user from session cookie for template pages"""
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    with get_db() as cur:
        cur.execute("""
            SELECT customer_id, name, email, phone, role, created_at 
            FROM Customer WHERE customer_id = %s
        """, (user_id,))
        row = cur.fetchone()
        if row:
            return {
                "customer_id": row[0],
                "name": row[1],
                "email": row[2],
                "phone": row[3],
                "role": row[4],
                "created_at": row[5]
            }
    return None


# ===== HEALTH CHECK =====
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "cinebook-api"}


# ===== AUTH HELPERS =====
def require_auth(request: Request):
    """Redirect to login if not authenticated"""
    user = request.session.get("user_id")
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    return None

def require_admin(request: Request):
    """Redirect if not admin"""
    user = request.session.get("user_id")
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    # Check role in session
    if request.session.get("role") != "ADMIN":
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    return None


# ===== PAGE ROUTES =====

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Home page - show featured movies or redirect to movies list"""
    user = await get_current_user(request)

    with get_db() as cur:
        # Get genres for filter dropdown
        cur.execute("SELECT genre_name FROM Genre ORDER BY genre_name")
        genres = [row[0] for row in cur.fetchall()]

        # Get some featured movies
        cur.execute("""
            SELECT m.movie_id, m.title, m.poster_url, m.rating
            FROM Movie m
            WHERE m.release_date <= CURRENT_DATE
            ORDER BY m.rating DESC NULLS LAST
            LIMIT 8
        """)
        featured = cur.fetchall()

    featured_movies = [{
        "movie_id": m[0], "title": m[1], "poster_url": m[2], "rating": m[3]
    } for m in featured]

    return templates.TemplateResponse(request, "index.html", {
        "user": user, "genres": genres, "featured_movies": featured_movies
    })


@app.get("/movies", response_class=HTMLResponse)
async def movies_page(request: Request, search: str = "", genre: str = "", language: str = "", certificate: str = "", min_rating: float = 0):
    """Movie listing page with filters"""
    user = await get_current_user(request)

    with get_db() as cur:
        # Build query with filters
        query = """
            SELECT DISTINCT m.movie_id, m.title, m.description, m.duration_min, m.language,
                   m.certificate, m.release_date, m.rating, m.poster_url,
                   STRING_AGG(g.genre_name, ', ') as genres
            FROM Movie m
            LEFT JOIN Movie_Genre mg ON m.movie_id = mg.movie_id
            LEFT JOIN Genre g ON mg.genre_id = g.genre_id
            WHERE 1=1
        """
        params = []

        if search:
            query += " AND m.title ILIKE %s"
            params.append(f"%{search}%")
        if genre:
            query += " AND g.genre_name = %s"
            params.append(genre)
        if language:
            query += " AND m.language = %s"
            params.append(language)
        if certificate:
            query += " AND m.certificate = %s"
            params.append(certificate)
        if min_rating > 0:
            query += " AND m.rating >= %s"
            params.append(min_rating)

        query += " GROUP BY m.movie_id ORDER BY m.title"

        cur.execute(query, params)
        movies = cur.fetchall()

        # Get genres for filter dropdown
        cur.execute("SELECT genre_name FROM Genre ORDER BY genre_name")
        genres = [row[0] for row in cur.fetchall()]

        # Get all distinct languages for filter dropdown
        cur.execute("SELECT DISTINCT language FROM Movie ORDER BY language")
        languages = [row[0] for row in cur.fetchall()]

    movie_list = [{
        "movie_id": m[0], "title": m[1], "description": m[2], "duration_min": m[3],
        "language": m[4], "certificate": m[5], "release_date": m[6], "rating": m[7],
        "poster_url": m[8], "genres": m[9].split(", ") if m[9] else []
    } for m in movies]

    return templates.TemplateResponse(request, "movies.html", {
        "user": user, "movies": movie_list,
        "genres": genres, "languages": languages,
        "filters": {"search": search, "genre": genre, "language": language,
                      "certificate": certificate, "min_rating": min_rating}
    })


@app.get("/movies/{movie_id}", response_class=HTMLResponse)
async def movie_detail(request: Request, movie_id: int):
    """Movie detail page with showtimes"""
    user = await get_current_user(request)

    with get_db() as cur:
        # Get movie details
        cur.execute("""
            SELECT m.movie_id, m.title, m.description, m.duration_min, m.language,
                   m.certificate, m.release_date, m.rating, m.poster_url,
                   STRING_AGG(g.genre_name, ', ') as genres
            FROM Movie m
            LEFT JOIN Movie_Genre mg ON m.movie_id = mg.movie_id
            LEFT JOIN Genre g ON mg.genre_id = g.genre_id
            WHERE m.movie_id = %s
            GROUP BY m.movie_id
        """, (movie_id,))
        movie = cur.fetchone()

        if not movie:
            raise HTTPException(status_code=404, detail="Movie not found")

        # Get upcoming shows with seats left
        cur.execute("""
            SELECT s.show_id, s.show_date, s.start_time, s.end_time,
                   t.name as theatre_name, t.city,
                   sc.screen_name, sc.screen_type,
                   sc.screen_id,
                   (SELECT COUNT(*) FROM Seat WHERE screen_id = sc.screen_id) as total_seats,
                   (SELECT COUNT(*) FROM Ticket t2
                    JOIN "show" s2 ON t2.show_id = s2.show_id
                    WHERE s2.show_id = s.show_id AND t2.status = 'ACTIVE') as booked_seats
            FROM "show" s
            JOIN Screen sc ON s.screen_id = sc.screen_id
            JOIN Theatre t ON sc.theatre_id = t.theatre_id
            WHERE s.movie_id = %s AND s.show_date >= CURRENT_DATE
            ORDER BY s.show_date, s.start_time
        """, (movie_id,))
        shows = cur.fetchall()

    movie_data = {
        "movie_id": movie[0], "title": movie[1], "description": movie[2],
        "duration_min": movie[3], "language": movie[4], "certificate": movie[5],
        "release_date": movie[6], "rating": movie[7], "poster_url": movie[8],
        "genres": movie[9].split(", ") if movie[9] else []
    }

    show_list = [{
        "show_id": s[0], "show_date": s[1], "start_time": s[2], "end_time": s[3],
        "theatre_name": s[4], "city": s[5], "screen_name": s[6], "screen_type": s[7],
        "seats_left": s[9] - s[10] if s[9] and s[10] is not None else 0,
        "total_seats": s[9] if s[9] else 0
    } for s in shows]

    return templates.TemplateResponse(request, "movie_detail.html", {
        "user": user, "movie": movie_data, "shows": show_list
    })


@app.get("/shows/{show_id}/seats", response_class=HTMLResponse)
async def seat_select(request: Request, show_id: int):
    """Seat selection page"""
    user = await get_current_user(request)
    if not user:
        flash(request, "Please login to book tickets", "warning")
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    
    with get_db() as cur:
        # Get show details with screen info
        cur.execute("""
            SELECT s.show_id, s.movie_id, s.show_date, s.start_time, s.end_time,
                   m.title as movie_title, m.duration_min,
                   t.name as theatre_name, t.city,
                   sc.screen_id, sc.screen_name, sc.screen_type
            FROM "show" s
            JOIN Movie m ON s.movie_id = m.movie_id
            JOIN Screen sc ON s.screen_id = sc.screen_id
            JOIN Theatre t ON sc.theatre_id = t.theatre_id
            WHERE s.show_id = %s
        """, (show_id,))
        show = cur.fetchone()
        
        if not show:
            raise HTTPException(status_code=404, detail="Show not found")
        
        # Get seats with pricing and availability
        cur.execute("""
            SELECT st.seat_id, st.row_label, st.seat_number, st.seat_category,
                   sp.price,
                   CASE WHEN t.ticket_id IS NOT NULL AND t.status = 'ACTIVE' THEN 'taken' ELSE 'available' END as status
            FROM Seat st
            JOIN Show_Pricing sp ON sp.show_id = %s AND sp.seat_category = st.seat_category
            LEFT JOIN Ticket t ON t.show_id = %s AND t.seat_id = st.seat_id AND t.status = 'ACTIVE'
            WHERE st.screen_id = %s
            ORDER BY st.row_label, st.seat_number
        """, (show_id, show_id, show[9]))
        seats = cur.fetchall()

    show_data = {
        "show_id": show[0], "movie_id": show[1], "show_date": show[2],
        "start_time": show[3], "end_time": show[4], "movie_title": show[5],
        "duration_min": show[6], "theatre_name": show[7], "city": show[8],
        "screen_name": show[10], "screen_type": show[11]
    }

    seat_list = [{
        "seat_id": s[0], "row_label": s[1], "seat_number": s[2],
        "seat_category": s[3], "price": s[4], "status": s[5]
    } for s in seats]

    # Group seats by row for template
    rows = {}
    for seat in seat_list:
        row = seat["row_label"]
        if row not in rows:
            rows[row] = []
        rows[row].append(seat)

    return templates.TemplateResponse(request, "seat_select.html", {
        "user": user, "show": show_data, "seats": seat_list, "rows": rows
    })


@app.post("/shows/{show_id}/book", response_class=HTMLResponse)
async def book_seats(request: Request, show_id: int, seat_ids: list[int] = Form(...), payment_method: str = Form("UPI")):
    """Process booking from seat selection"""
    user = await get_current_user(request)
    if not user:
        flash(request, "Please login to book tickets", "warning")
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    if not seat_ids:
        flash(request, "Please select at least one seat", "error")
        return RedirectResponse(url=f"/shows/{show_id}/seats", status_code=status.HTTP_303_SEE_OTHER)

    # Validate seat count (max 6)
    if len(seat_ids) > 6:
        flash(request, "Maximum 6 seats per booking", "error")
        return RedirectResponse(url=f"/shows/{show_id}/seats", status_code=status.HTTP_303_SEE_OTHER)

    # Store selected seats in session
    request.session["selected_seats"] = seat_ids
    request.session["show_id"] = show_id
    request.session["payment_method"] = payment_method

    return RedirectResponse(url="/checkout", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/checkout", response_class=HTMLResponse)
async def checkout_page(request: Request):
    """Checkout page with payment method selection"""
    user = await get_current_user(request)
    if not user:
        flash(request, "Please login to continue", "warning")
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    
    seat_ids = request.session.get("selected_seats", [])
    show_id = request.session.get("show_id")
    payment_method = request.session.get("payment_method", "UPI")
    
    if not seat_ids or not show_id:
        flash(request, "No seats selected", "error")
        return RedirectResponse(url="/movies", status_code=status.HTTP_303_SEE_OTHER)
    
    with get_db() as cur:
        # Get show and seat details
        cur.execute("""
            SELECT s.show_id, s.show_date, s.start_time, m.title, m.duration_min,
                   t.name as theatre_name, sc.screen_name
            FROM "show" s
            JOIN Movie m ON s.movie_id = m.movie_id
            JOIN Screen sc ON s.screen_id = sc.screen_id
            JOIN Theatre t ON sc.theatre_id = t.theatre_id
            WHERE s.show_id = %s
        """, (show_id,))
        show = cur.fetchone()
        
        cur.execute("""
            SELECT st.seat_id, st.row_label, st.seat_number, st.seat_category, sp.price
            FROM Seat st
            JOIN Show_Pricing sp ON sp.show_id = %s AND sp.seat_category = st.seat_category
            WHERE st.seat_id = ANY(%s)
            ORDER BY st.row_label, st.seat_number
        """, (show_id, seat_ids))
        seats = cur.fetchall()
    
    total = sum(s[4] for s in seats)
    
    show_data = {"show_id": show[0], "show_date": show[1], "start_time": show[2],
                 "movie_title": show[3], "duration_min": show[4],
                 "theatre_name": show[5], "screen_name": show[6]}
    
    seat_list = [{"seat_id": s[0], "row_label": s[1], "seat_number": s[2],
                  "seat_category": s[3], "price": s[4]} for s in seats]
    
    return templates.TemplateResponse(request, "checkout.html", {
        "user": user, "show": show_data,
        "seats": seat_list, "total": total, "payment_method": payment_method
    })


@app.post("/book", response_class=HTMLResponse)
async def process_booking(request: Request, payment_method: str = Form(None)):
    """Final booking confirmation - creates booking, tickets, payment"""
    user = await get_current_user(request)
    if not user:
        flash(request, "Session expired, please login again", "error")
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    seat_ids = request.session.get("selected_seats", [])
    show_id = request.session.get("show_id")
    # Use form payment_method if provided, otherwise fall back to session
    payment_method = payment_method or request.session.get("payment_method", "UPI")

    if not seat_ids or not show_id:
        flash(request, "Invalid booking session", "error")
        return RedirectResponse(url="/movies", status_code=status.HTTP_303_SEE_OTHER)

    # Validate seat count (max 6)
    if len(seat_ids) > 6:
        flash(request, "Maximum 6 seats per booking", "error")
        return RedirectResponse(url=f"/shows/{show_id}/seats", status_code=status.HTTP_303_SEE_OTHER)

    # Call booking transaction
    from services.booking_service import create_booking

    try:
        with get_db() as cur:
            result = create_booking(cur, user["customer_id"], show_id, seat_ids, payment_method)
            # Clear session
            request.session.pop("selected_seats", None)
            request.session.pop("show_id", None)
            request.session.pop("payment_method", None)

            flash(request, "Booking confirmed!", "success")
            return RedirectResponse(url=f"/confirmation/{result['booking_id']}",
                                   status_code=status.HTTP_303_SEE_OTHER)
    except ValueError as e:
        # Only flash user-friendly ValueError messages
        flash(request, str(e), "error")
        return RedirectResponse(url=f"/shows/{show_id}/seats", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        # Generic error for unexpected exceptions
        flash(request, "Booking failed. Please try again.", "error")
        return RedirectResponse(url=f"/shows/{show_id}/seats", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/confirmation/{booking_id}", response_class=HTMLResponse)
async def confirmation(request: Request, booking_id: int):
    """Booking confirmation page (looks like a ticket)"""
    user = await get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    
    with get_db() as cur:
        # Get full booking details
        cur.execute("""
            SELECT b.booking_id, b.booking_time, b.total_amount, b.status,
                   s.show_id, s.show_date, s.start_time, s.end_time,
                   m.title, m.duration_min, m.poster_url,
                   t.name as theatre_name, t.city, t.address,
                   sc.screen_name, sc.screen_type,
                   STRING_AGG(st.row_label || '-' || st.seat_number, ', ') as seats,
                   STRING_AGG(st.seat_category, ', ') as seat_categories,
                   STRING_AGG(tk.price::text, ', ') as prices
            FROM Booking b
            JOIN "show" s ON b.show_id = s.show_id
            JOIN Movie m ON s.movie_id = m.movie_id
            JOIN Screen sc ON s.screen_id = sc.screen_id
            JOIN Theatre t ON sc.theatre_id = t.theatre_id
            JOIN Ticket tk ON tk.booking_id = b.booking_id
            JOIN Seat st ON tk.seat_id = st.seat_id
            WHERE b.booking_id = %s AND b.customer_id = %s
            GROUP BY b.booking_id, s.show_id, m.movie_id, t.theatre_id, sc.screen_id
        """, (booking_id, user["customer_id"]))
        booking = cur.fetchone()
        
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")
        
        # Get payment
        cur.execute("""
            SELECT payment_id, amount, method, status, paid_at
            FROM Payment WHERE booking_id = %s
        """, (booking_id,))
        payment = cur.fetchone()
    
    booking_data = {
        "booking_id": booking[0], "booking_time": booking[1], "total_amount": booking[2],
        "status": booking[3], "show_id": booking[4], "show_date": booking[5],
        "start_time": booking[6], "end_time": booking[7],
        "movie_title": booking[8], "duration_min": booking[9], "poster_url": booking[10],
        "theatre_name": booking[11], "city": booking[12], "address": booking[13],
        "screen_name": booking[14], "screen_type": booking[15],
        "seats": booking[16].split(", ") if booking[16] else [],
        "seat_categories": booking[17].split(", ") if booking[17] else [],
        "prices": [int(p) for p in booking[18].split(", ")] if booking[18] else []
    }
    
    payment_data = {
        "payment_id": payment[0], "amount": payment[1], "method": payment[2],
        "status": payment[3], "paid_at": payment[4]
    } if payment else None
    
    return templates.TemplateResponse(request, "confirmation.html", {
        "user": user, "booking": booking_data, "payment": payment_data
    })


@app.get("/my-bookings", response_class=HTMLResponse)
async def my_bookings(request: Request):
    """User's booking history"""
    user = await get_current_user(request)
    if not user:
        flash(request, "Please login to view bookings", "warning")
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    from datetime import datetime, timedelta

    with get_db() as cur:
        cur.execute("""
            SELECT b.booking_id, b.booking_time, b.total_amount, b.status,
                   s.show_id, s.show_date, s.start_time,
                   m.title, m.poster_url,
                   t.name as theatre_name, sc.screen_name,
                   STRING_AGG(st.row_label || '-' || st.seat_number, ', ') as seats,
                   p.status as payment_status
            FROM Booking b
            JOIN "show" s ON b.show_id = s.show_id
            JOIN Movie m ON s.movie_id = m.movie_id
            JOIN Screen sc ON s.screen_id = sc.screen_id
            JOIN Theatre t ON sc.theatre_id = t.theatre_id
            JOIN Ticket tk ON tk.booking_id = b.booking_id
            JOIN Seat st ON tk.seat_id = st.seat_id
            LEFT JOIN Payment p ON p.booking_id = b.booking_id
            WHERE b.customer_id = %s
            GROUP BY b.booking_id, s.show_id, m.movie_id, t.theatre_id, sc.screen_id, p.status
            ORDER BY b.booking_time DESC
        """, (user["customer_id"],))
        bookings = cur.fetchall()

    booking_list = []
    for b in bookings:
        show_dt = datetime.combine(b[5], b[6])  # show_date, start_time
        can_cancel = (b[3] == 'CONFIRMED' and show_dt > datetime.now() + timedelta(hours=2))

        booking_list.append({
            "booking_id": b[0], "booking_time": b[1], "total_amount": b[2], "status": b[3],
            "show_id": b[4], "show_date": b[5], "start_time": b[6],
            "movie_title": b[7], "poster_url": b[8],
            "theatre_name": b[9], "screen_name": b[10],
            "seats": b[11].split(", ") if b[11] else [],
            "payment_status": b[12],
            "can_cancel": can_cancel
        })

    return templates.TemplateResponse(request, "my_bookings.html", {
        "user": user, "bookings": booking_list
    })


@app.post("/bookings/{booking_id}/cancel", response_class=HTMLResponse)
async def cancel_booking(request: Request, booking_id: int):
    """Cancel a booking"""
    user = await get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    from services.cancellation_service import cancel_booking as cancel_booking_service

    try:
        with get_db() as cur:
            result = cancel_booking_service(cur, user["customer_id"], booking_id)
            flash(request, "Booking cancelled and refunded", "success")
    except ValueError as e:
        flash(request, str(e), "error")
    except Exception as e:
        flash(request, "Cancellation failed. Please try again.", "error")

    return RedirectResponse(url="/my-bookings", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page"""
    user = await get_current_user(request)
    if user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request, "login.html", {"user": None})


@app.post("/login", response_class=HTMLResponse)
async def login_submit(request: Request, email: str = Form(...), password: str = Form(...)):
    """Process login form"""
    with get_db() as cur:
        cur.execute("""
            SELECT customer_id, name, email, phone, role, password_hash
            FROM Customer WHERE email = %s
        """, (email,))
        user = cur.fetchone()
    
    if user and verify_password(password, user[5]):
        request.session["user_id"] = user[0]
        request.session["name"] = user[1]
        request.session["email"] = user[2]
        request.session["role"] = user[4]
        flash(request, f"Welcome back, {user[1]}!", "success")
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    else:
        flash(request, "Invalid email or password", "error")
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Register page"""
    user = await get_current_user(request)
    if user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request, "register.html", {"user": None})


@app.post("/register", response_class=HTMLResponse)
async def register_submit(request: Request, name: str = Form(...), email: str = Form(...),
                          phone: str = Form(...), password: str = Form(...),
                          confirm_password: str = Form(...)):
    """Process registration form"""
    if password != confirm_password:
        flash(request, "Passwords do not match", "error")
        return RedirectResponse(url="/register", status_code=status.HTTP_303_SEE_OTHER)
    
    if len(password) < 8:
        flash(request, "Password must be at least 8 characters", "error")
        return RedirectResponse(url="/register", status_code=status.HTTP_303_SEE_OTHER)
    
    with get_db() as cur:
        # Check if email/phone exists
        cur.execute("SELECT 1 FROM Customer WHERE email = %s OR phone = %s", (email, phone))
        if cur.fetchone():
            flash(request, "Email or phone already registered", "error")
            return RedirectResponse(url="/register", status_code=status.HTTP_303_SEE_OTHER)
        
        # Create user
        hashed = hash_password(password)
        cur.execute("""
            INSERT INTO Customer (name, email, phone, password_hash, role)
            VALUES (%s, %s, %s, %s, 'CUSTOMER')
            RETURNING customer_id
        """, (name, email, phone, hashed))
        user_id = cur.fetchone()[0]
        
        request.session["user_id"] = user_id
        request.session["name"] = name
        request.session["email"] = email
        request.session["role"] = "CUSTOMER"
        
        flash(request, "Registration successful!", "success")
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/logout")
async def logout(request: Request):
    """Logout - clear session"""
    request.session.clear()
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


# ===== ADMIN ROUTES =====
@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Admin dashboard page"""
    user = await get_current_user(request)
    if not user or user.get("role") != "ADMIN":
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    with get_db() as cur:
        from services.report_service import get_admin_dashboard_summary
        summary = get_admin_dashboard_summary(cur)

    stats = {
        "total_tickets_sold": summary[0] if summary else 0,
        "total_revenue": summary[1] if summary else 0,
        "avg_ticket_price": summary[2] if summary else 0,
        "highest_ticket_price": summary[3] if summary else 0,
        "lowest_ticket_price": summary[4] if summary else 0,
    }

    return templates.TemplateResponse(request, "admin.html", {
        "user": user, "stats": stats
    })


@app.get("/reports/revenue-by-movie", response_class=HTMLResponse)
async def report_revenue_by_movie(request: Request, date_from: str = "", date_to: str = ""):
    """Revenue by movie report"""
    user = await get_current_user(request)
    if not user or user.get("role") != "ADMIN":
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    from datetime import date
    df = date.fromisoformat(date_from) if date_from else None
    dt = date.fromisoformat(date_to) if date_to else None

    with get_db() as cur:
        from services.report_service import get_revenue_by_movie
        rows = get_revenue_by_movie(cur, df, dt)

    report = [{
        "movie_id": r[0], "title": r[1], "total_revenue": r[2],
        "tickets_sold": r[3], "avg_price": r[4]
    } for r in rows]

    return templates.TemplateResponse(request, "admin_reports.html", {
        "user": user, "report": report, "report_type": "revenue-by-movie",
        "filters": {"date_from": date_from, "date_to": date_to}
    })


@app.get("/reports/occupancy", response_class=HTMLResponse)
async def report_occupancy(request: Request, date_from: str = "", date_to: str = "", theatre_id: int = None, above_avg_only: bool = False):
    """Occupancy report"""
    user = await get_current_user(request)
    if not user or user.get("role") != "ADMIN":
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    from datetime import date
    df = date.fromisoformat(date_from) if date_from else None
    dt = date.fromisoformat(date_to) if date_to else None

    with get_db() as cur:
        from services.report_service import get_occupancy
        rows = get_occupancy(cur, df, dt, theatre_id, above_avg_only)

    report = [{
        "show_id": r[0], "movie": r[1], "theatre": r[2], "screen": r[3],
        "show_date": r[4], "start_time": r[5], "total_seats": r[6],
        "booked_seats": r[7], "seats_left": r[8], "occupancy_pct": r[9]
    } for r in rows]

    # Get theatres for filter
    with get_db() as cur:
        cur.execute("SELECT theatre_id, name FROM Theatre ORDER BY name")
        theatres = cur.fetchall()

    return templates.TemplateResponse(request, "admin_reports.html", {
        "user": user, "report": report, "report_type": "occupancy",
        "theatres": theatres,
        "filters": {"date_from": date_from, "date_to": date_to, "theatre_id": theatre_id, "above_avg_only": above_avg_only}
    })


@app.get("/reports/top-customers", response_class=HTMLResponse)
async def report_top_customers(request: Request, limit: int = 10, date_from: str = "", date_to: str = ""):
    """Top customers report"""
    user = await get_current_user(request)
    if not user or user.get("role") != "ADMIN":
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    from datetime import date
    df = date.fromisoformat(date_from) if date_from else None
    dt = date.fromisoformat(date_to) if date_to else None

    with get_db() as cur:
        from services.report_service import get_top_customers
        rows = get_top_customers(cur, limit, df, dt)

    report = [{
        "customer_id": r[0], "name": r[1], "email": r[2],
        "bookings_count": r[3], "total_spent": r[4]
    } for r in rows]

    return templates.TemplateResponse(request, "admin_reports.html", {
        "user": user, "report": report, "report_type": "top-customers",
        "filters": {"limit": limit, "date_from": date_from, "date_to": date_to}
    })


@app.get("/reports/daily-sales", response_class=HTMLResponse)
async def report_daily_sales(request: Request, days: int = 7):
    """Daily sales report"""
    user = await get_current_user(request)
    if not user or user.get("role") != "ADMIN":
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    with get_db() as cur:
        from services.report_service import get_daily_sales
        rows = get_daily_sales(cur, days)

    report = [{
        "sale_date": r[0], "bookings": r[1], "revenue": r[2]
    } for r in rows]

    return templates.TemplateResponse(request, "admin_reports.html", {
        "user": user, "report": report, "report_type": "daily-sales",
        "filters": {"days": days}
    })


@app.get("/reports/unsold-movies", response_class=HTMLResponse)
async def report_unsold_movies(request: Request):
    """Unsold movies report"""
    user = await get_current_user(request)
    if not user or user.get("role") != "ADMIN":
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    with get_db() as cur:
        from services.report_service import get_unsold_movies
        rows = get_unsold_movies(cur)

    report = [{
        "movie_id": r[0], "title": r[1], "language": r[2], "certificate": r[3]
    } for r in rows]

    return templates.TemplateResponse(request, "admin_reports.html", {
        "user": user, "report": report, "report_type": "unsold-movies",
        "filters": {}
    })


@app.get("/reports/unbooked-customers", response_class=HTMLResponse)
async def report_unbooked_customers(request: Request):
    """Customers who never booked report"""
    user = await get_current_user(request)
    if not user or user.get("role") != "ADMIN":
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    with get_db() as cur:
        from services.report_service import get_unbooked_customers
        rows = get_unbooked_customers(cur)

    report = [{
        "customer_id": r[0], "name": r[1], "email": r[2], "phone": r[3], "created_at": r[4]
    } for r in rows]

    return templates.TemplateResponse(request, "admin_reports.html", {
        "user": user, "report": report, "report_type": "unbooked-customers",
        "filters": {}
    })


@app.get("/reports/busiest-screens", response_class=HTMLResponse)
async def report_busiest_screens(request: Request):
    """Busiest screens report"""
    user = await get_current_user(request)
    if not user or user.get("role") != "ADMIN":
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    with get_db() as cur:
        from services.report_service import get_busiest_screens
        rows = get_busiest_screens(cur)

    report = [{
        "theatre_id": r[0], "theatre_name": r[1], "city": r[2],
        "screen_id": r[3], "screen_name": r[4], "screen_type": r[5],
        "total_shows": r[6], "tickets_sold": r[7], "total_revenue": r[8]
    } for r in rows]

    return templates.TemplateResponse(request, "admin_reports.html", {
        "user": user, "report": report, "report_type": "busiest-screens",
        "filters": {}
    })


# ===== API ROUTES (to be added later) =====
# from routers import auth, movies, theatres, shows, bookings, reports
# app.include_router(auth.router, prefix="/auth", tags=["auth"])
# ...

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


# ===== ERROR HANDLERS =====
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    user = await get_current_user(request)
    return templates.TemplateResponse(request, "404.html", {"user": user}, status_code=404)

@app.exception_handler(500)
async def server_error_handler(request: Request, exc: Exception):
    user = await get_current_user(request)
    return templates.TemplateResponse(request, "error.html", {"user": user}, status_code=500)
