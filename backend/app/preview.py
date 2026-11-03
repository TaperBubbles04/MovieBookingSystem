"""Stand-alone preview server for the customer templates. Development only.

Run from the backend folder:   python app/preview.py
Then open http://127.0.0.1:8001

Needs: pip install fastapi uvicorn jinja2 python-multipart itsdangerous
No database: it uses fake data from mock_data.py and fakes login (any email
and password works). Route function names, URLs and template variables copy
backend/main.py exactly, so a page that works here works in the real app.
Keep it in sync when main.py changes.
"""
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

import mock_data

HERE = Path(__file__).parent
app = FastAPI(title="CineBook template preview")
app.add_middleware(SessionMiddleware, secret_key="preview-only-not-a-secret", max_age=1800)


def flash(request: Request, message: str, category: str = "info"):
    request.session.setdefault("_flashes", [])
    request.session["_flashes"] = request.session["_flashes"] + [{"message": message, "category": category}]


def flash_context_processor(request: Request):
    return {"flashes": request.session.pop("_flashes", [])}


templates = Jinja2Templates(directory=HERE / "templates", context_processors=[flash_context_processor])
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")


async def get_current_user(request: Request):
    if not request.session.get("user_id"):
        return None
    return {"customer_id": request.session["user_id"], "name": request.session["name"],
            "email": request.session["email"], "phone": "9876543210",
            "role": request.session["role"], "created_at": None}


def login_redirect(request: Request, message: str):
    flash(request, message, "warning")
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    user = await get_current_user(request)
    return templates.TemplateResponse(request, "index.html", {"user": user})


@app.get("/movies", response_class=HTMLResponse)
async def movies_page(request: Request, search: str = "", genre: str = "", language: str = "",
                      certificate: str = "", min_rating: float = 0):
    user = await get_current_user(request)
    return templates.TemplateResponse(request, "movies.html", {
        "user": user,
        "movies": mock_data.get_movies(search, genre, language, certificate, min_rating),
        "genres": sorted(mock_data.GENRES),
        "filters": {"search": search, "genre": genre, "language": language,
                    "certificate": certificate, "min_rating": min_rating},
    })


@app.get("/movies/{movie_id}", response_class=HTMLResponse)
async def movie_detail(request: Request, movie_id: int):
    user = await get_current_user(request)
    movie = mock_data.get_movie(movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return templates.TemplateResponse(request, "movie_detail.html", {
        "user": user, "movie": movie, "shows": mock_data.get_movie_shows(movie_id)})


@app.get("/shows/{show_id}/seats", response_class=HTMLResponse)
async def seat_select(request: Request, show_id: int):
    user = await get_current_user(request)
    if not user:
        return login_redirect(request, "Please login to book tickets")
    page = mock_data.get_seat_page(show_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Show not found")
    show, seats, rows = page
    return templates.TemplateResponse(request, "seat_select.html", {
        "user": user, "show": show, "seats": seats, "rows": rows})


@app.post("/shows/{show_id}/book", response_class=HTMLResponse)
async def book_seats(request: Request, show_id: int, seat_ids: list[int] = Form(...),
                     payment_method: str = Form(...)):
    user = await get_current_user(request)
    if not user:
        return login_redirect(request, "Please login to book tickets")
    request.session["selected_seats"] = seat_ids
    request.session["show_id"] = show_id
    request.session["payment_method"] = payment_method
    return RedirectResponse(url="/checkout", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/checkout", response_class=HTMLResponse)
async def checkout_page(request: Request):
    user = await get_current_user(request)
    if not user:
        return login_redirect(request, "Please login to continue")
    seat_ids = request.session.get("selected_seats", [])
    show_id = request.session.get("show_id")
    if not seat_ids or not show_id:
        flash(request, "No seats selected", "error")
        return RedirectResponse(url="/movies", status_code=status.HTTP_303_SEE_OTHER)
    show, seats, total = mock_data.get_checkout(show_id, seat_ids)
    return templates.TemplateResponse(request, "checkout.html", {
        "user": user, "show": show, "seats": seats, "total": total,
        "payment_method": request.session.get("payment_method", "UPI")})


@app.post("/book", response_class=HTMLResponse)
async def process_booking(request: Request):
    user = await get_current_user(request)
    if not user:
        flash(request, "Session expired, please login again", "error")
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    seat_ids = request.session.get("selected_seats", [])
    show_id = request.session.get("show_id")
    payment_method = request.session.get("payment_method", "UPI")
    if not seat_ids or not show_id:
        flash(request, "Invalid booking session", "error")
        return RedirectResponse(url="/movies", status_code=status.HTTP_303_SEE_OTHER)
    try:
        result = mock_data.create_booking(user["customer_id"], show_id, seat_ids, payment_method)
    except ValueError as e:
        flash(request, str(e), "error")
        return RedirectResponse(url=f"/shows/{show_id}/seats", status_code=status.HTTP_303_SEE_OTHER)
    for key in ("selected_seats", "show_id", "payment_method"):
        request.session.pop(key, None)
    flash(request, "Booking confirmed!", "success")
    return RedirectResponse(url=f"/confirmation/{result['booking_id']}", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/confirmation/{booking_id}", response_class=HTMLResponse)
async def confirmation(request: Request, booking_id: int):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    found = mock_data.get_confirmation(user["customer_id"], booking_id)
    if not found:
        raise HTTPException(status_code=404, detail="Booking not found")
    booking, payment = found
    return templates.TemplateResponse(request, "confirmation.html", {
        "user": user, "booking": booking, "payment": payment})


@app.get("/my-bookings", response_class=HTMLResponse)
async def my_bookings(request: Request):
    user = await get_current_user(request)
    if not user:
        return login_redirect(request, "Please login to view bookings")
    return templates.TemplateResponse(request, "my_bookings.html", {
        "user": user, "bookings": mock_data.get_my_bookings(user["customer_id"])})


@app.post("/bookings/{booking_id}/cancel", response_class=HTMLResponse)
async def cancel_booking(request: Request, booking_id: int):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    try:
        mock_data.cancel_booking(user["customer_id"], booking_id)
        flash(request, "Booking cancelled and refunded", "success")
    except ValueError as e:
        flash(request, str(e), "error")
    return RedirectResponse(url="/my-bookings", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if await get_current_user(request):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request, "login.html", {"user": None})


@app.post("/login", response_class=HTMLResponse)
async def login_submit(request: Request, email: str = Form(...), password: str = Form(...)):
    # Preview only: any email and password logs in. An email starting with
    # "admin" logs in as ADMIN so the admin link can be checked.
    customer_id = sum(ord(c) for c in email)
    request.session.update(user_id=customer_id, name=email.split("@")[0].title(), email=email,
                           role="ADMIN" if email.startswith("admin") else "CUSTOMER")
    mock_data.seed_sample_bookings(customer_id)
    flash(request, f"Welcome back, {request.session['name']}!", "success")
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    if await get_current_user(request):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request, "register.html", {"user": None})


@app.post("/register", response_class=HTMLResponse)
async def register_submit(request: Request, name: str = Form(...), email: str = Form(...),
                          phone: str = Form(...), password: str = Form(...),
                          confirm_password: str = Form(...)):
    if password != confirm_password:
        flash(request, "Passwords do not match", "error")
        return RedirectResponse(url="/register", status_code=status.HTTP_303_SEE_OTHER)
    if len(password) < 8:
        flash(request, "Password must be at least 8 characters", "error")
        return RedirectResponse(url="/register", status_code=status.HTTP_303_SEE_OTHER)
    request.session.update(user_id=sum(ord(c) for c in email), name=name, email=email, role="CUSTOMER")
    flash(request, "Registration successful!", "success")
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


# ---- Not in main.py yet: the 404/500 handlers I've asked Tharanesh to add ----

@app.get("/preview/error")
async def preview_error():
    raise RuntimeError("Preview of the error page")


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException):
    user = await get_current_user(request)
    name = "404.html" if exc.status_code == 404 else "error.html"
    return templates.TemplateResponse(request, name, {"user": user}, status_code=exc.status_code)


@app.exception_handler(Exception)
async def server_error(request: Request, exc: Exception):
    return templates.TemplateResponse(request, "error.html", {"user": None}, status_code=500)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("preview:app", host="127.0.0.1", port=8001, reload=True, app_dir=str(HERE))
