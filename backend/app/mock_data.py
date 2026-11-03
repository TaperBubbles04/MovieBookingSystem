"""Fake data for the template preview (backend/app/preview.py).

Mirrors db/seed.sql (same movies, theatres, screens and seat layouts) but
schedules shows relative to today so there is always something to book.
Each get_* function returns exactly what the matching route in
backend/main.py passes to its template, including the Python types psycopg
returns (date, time, datetime, Decimal). Nothing here is used by the real app.
"""
import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal

GENRES = ["Action", "Drama", "Comedy", "Thriller", "Sci-Fi", "Romance", "Animation", "Horror"]

_U = "https://images.unsplash.com/photo-"
MOVIES = [
    (1, "Leo", "A mild-mannered cafe owner in Kashmir becomes a local hero, drawing the attention of a ruthless drug cartel claiming he is their former cohort.", 164, "Tamil", "UA", "2026-10-16", "8.1", _U + "1536440136628-849c177e76a1?w=600", ["Action", "Thriller"]),
    (2, "Vikram", "A special investigator discovers a case of serial killings is not what it seems to be, leading to a high-stakes war between rival vigilante and syndicate factions.", 174, "Tamil", "UA", "2026-09-25", "8.6", _U + "1489599849927-2ee91cede3ba?w=600", ["Action", "Thriller"]),
    (3, "Jawan", "A prison warden recruits inmates to commit high-profile heists that expose corruption and bring justice to everyday citizens.", 169, "Hindi", "UA", "2026-10-02", "7.8", _U + "1517604931442-7e0c8ed2963c?w=600", ["Action", "Drama"]),
    (4, "Stree 2", "The town of Chanderi faces a new supernatural terror in the form of Sarkata, forcing Vicky and his friends to reunite for a rescue mission.", 147, "Hindi", "UA", "2026-10-10", "8.2", _U + "1509198397868-475647b2a1e5?w=600", ["Comedy", "Horror"]),
    (5, "Oppenheimer", "The story of theoretical physicist J. Robert Oppenheimer and his role in designing the atomic bomb during World War II.", 180, "English", "A", "2026-08-15", "8.9", _U + "1440404653325-ab127d49abc1?w=600", ["Drama", "Thriller"]),
    (6, "Dune: Part Two", "Paul Atreides unites with Chani and the Fremen while on a warpath of revenge against the conspirators who destroyed his family.", 166, "English", "UA", "2026-09-12", "8.8", _U + "1518709268805-4e9042af9f23?w=600", ["Sci-Fi", "Action", "Drama"]),
    (7, "Kalki 2898 AD", "In a post-apocalyptic desert city, a bounty hunter and an immortal warrior cross paths to protect a prophesied child.", 181, "Telugu", "UA", "2026-10-09", "8.0", _U + "1508739773434-c26b3d09e071?w=600", ["Sci-Fi", "Action"]),
    (8, "Hi Nanna", "A doting single father begins to narrate the story of his missing wife to his six-year-old daughter with cystic fibrosis.", 155, "Telugu", "U", "2026-09-20", "8.3", _U + "1516589178581-6cd7833ae3b2?w=600", ["Drama", "Romance"]),
    (9, "Spider-Man: Across the Spider-Verse", "Miles Morales catapults across the Multiverse, where he encounters a team of Spider-People charged with protecting its very existence.", 140, "English", "U", "2026-08-28", "8.7", _U + "1635805737707-575885ab0820?w=600", ["Animation", "Action", "Sci-Fi"]),
    (10, "Kanguva", "A tribal warrior's fierce struggle to save his people a millennium ago is mysteriously linked to a shadow cop in the present.", 154, "Tamil", "UA", "2026-11-14", "7.5", _U + "1574375927938-d5a98e8ffe85?w=600", ["Action", "Drama"]),
]
MOVIES = [{
    "movie_id": m[0], "title": m[1], "description": m[2], "duration_min": m[3],
    "language": m[4], "certificate": m[5], "release_date": date.fromisoformat(m[6]),
    "rating": Decimal(m[7]), "poster_url": m[8], "genres": m[9],
} for m in MOVIES]

THEATRES = {
    1: {"name": "PVR Phoenix Marketcity", "city": "Chennai",
        "address": "142, Velachery Main Rd, Velachery, Chennai, Tamil Nadu 600042"},
    2: {"name": "INOX Mantri Square", "city": "Bengaluru",
        "address": "No. 1, Sampige Rd, Malleshwaram, Bengaluru, Karnataka 560003"},
}

# screen_id: (theatre_id, name, type, rows, seats per row, premium rows)
# The last row of every screen is RECLINER, as in the seed.
SCREENS = {
    1: (1, "Screen 1", "IMAX", "ABCDEF", 10, "DE"),
    2: (1, "Screen 2", "3D", "ABCDE", 10, "D"),
    3: (1, "Screen 3", "2D", "ABCDE", 8, "D"),
    4: (2, "Screen 1", "IMAX", "ABCDEF", 10, "DE"),
    5: (2, "Screen 2", "2D", "ABCDE", 10, "D"),
}

PRICES = {  # screen type -> category -> rupees (weekday prices from the seed)
    "IMAX": {"REGULAR": 220, "PREMIUM": 320, "RECLINER": 480},
    "3D": {"REGULAR": 180, "PREMIUM": 260, "RECLINER": 400},
    "2D": {"REGULAR": 150, "PREMIUM": 220, "RECLINER": 350},
}


def _build_seats():
    seats, seat_id = {}, 0
    for screen_id, (_, _, _, rows, per_row, premium) in SCREENS.items():
        for row in rows:
            category = "RECLINER" if row == rows[-1] else "PREMIUM" if row in premium else "REGULAR"
            for number in range(1, per_row + 1):
                seat_id += 1
                seats[seat_id] = {"seat_id": seat_id, "screen_id": screen_id, "row_label": row,
                                  "seat_number": number, "seat_category": category}
    return seats


def _build_shows():
    """Movies 1-9 play on two screens a day for the next 5 days. Kanguva has none."""
    slots = [time(10, 0), time(14, 0), time(18, 30), time(21, 45)]
    shows = {}
    for day in range(5):
        show_date = date.today() + timedelta(days=day)
        for movie in MOVIES[:9]:
            for k in range(2):
                screen_id = (movie["movie_id"] + day + 2 * k) % 5 + 1
                start = slots[(movie["movie_id"] + k + day) % len(slots)]
                end = (datetime.combine(show_date, start) + timedelta(minutes=movie["duration_min"])).time()
                show_id = len(shows) + 1
                shows[show_id] = {"show_id": show_id, "movie_id": movie["movie_id"],
                                  "screen_id": screen_id, "show_date": show_date,
                                  "start_time": start, "end_time": end}
    return shows


SEATS = _build_seats()
SHOWS = _build_shows()
TAKEN = {}  # show_id -> set of seat_ids with an ACTIVE ticket
for _s in SHOWS.values():
    _ids = [i for i, seat in SEATS.items() if seat["screen_id"] == _s["screen_id"]]
    _rng = random.Random(_s["show_id"])
    TAKEN[_s["show_id"]] = set(_rng.sample(_ids, _rng.randint(4, len(_ids) // 3)))

BOOKINGS = {}  # booking_id -> booking record


def _movie(movie_id):
    return next(m for m in MOVIES if m["movie_id"] == movie_id)


def _show_info(show_id):
    s = SHOWS[show_id]
    theatre_id, screen_name, screen_type, *_ = SCREENS[s["screen_id"]]
    return s, _movie(s["movie_id"]), THEATRES[theatre_id], screen_name, screen_type


def _price(show_id, seat_id):
    return PRICES[SCREENS[SHOWS[show_id]["screen_id"]][2]][SEATS[seat_id]["seat_category"]]


def _label(seat_id):
    return f"{SEATS[seat_id]['row_label']}-{SEATS[seat_id]['seat_number']}"


# ---- One function per route in backend/main.py ----

def get_movies(search="", genre="", language="", certificate="", min_rating=0):
    result = []
    for m in MOVIES:
        if search and search.lower() not in m["title"].lower():
            continue
        if genre and genre not in m["genres"]:
            continue
        if language and m["language"] != language:
            continue
        if certificate and m["certificate"] != certificate:
            continue
        if min_rating and m["rating"] < Decimal(str(min_rating)):
            continue
        result.append(m)
    return sorted(result, key=lambda m: m["title"])


def get_movie(movie_id):
    return next((m for m in MOVIES if m["movie_id"] == movie_id), None)


def get_movie_shows(movie_id):
    result = []
    for s in sorted(SHOWS.values(), key=lambda s: (s["show_date"], s["start_time"])):
        if s["movie_id"] != movie_id:
            continue
        theatre_id, screen_name, screen_type, *_ = SCREENS[s["screen_id"]]
        result.append({"show_id": s["show_id"], "show_date": s["show_date"],
                       "start_time": s["start_time"], "end_time": s["end_time"],
                       "theatre_name": THEATRES[theatre_id]["name"],
                       "city": THEATRES[theatre_id]["city"],
                       "screen_name": screen_name, "screen_type": screen_type})
    return result


def get_seat_page(show_id):
    """Returns (show, seats, rows) like seat_select(), or None."""
    if show_id not in SHOWS:
        return None
    s, movie, theatre, screen_name, screen_type = _show_info(show_id)
    show = {"show_id": show_id, "movie_id": movie["movie_id"], "show_date": s["show_date"],
            "start_time": s["start_time"], "end_time": s["end_time"],
            "movie_title": movie["title"], "duration_min": movie["duration_min"],
            "theatre_name": theatre["name"], "city": theatre["city"],
            "screen_name": screen_name, "screen_type": screen_type}
    seats = [{"seat_id": i, "row_label": seat["row_label"], "seat_number": seat["seat_number"],
              "seat_category": seat["seat_category"], "price": _price(show_id, i),
              "status": "taken" if i in TAKEN[show_id] else "available"}
             for i, seat in SEATS.items() if seat["screen_id"] == s["screen_id"]]
    rows = {}
    for seat in seats:
        rows.setdefault(seat["row_label"], []).append(seat)
    return show, seats, rows


def get_checkout(show_id, seat_ids):
    """Returns (show, seats, total) like checkout_page()."""
    s, movie, theatre, screen_name, _ = _show_info(show_id)
    show = {"show_id": show_id, "show_date": s["show_date"], "start_time": s["start_time"],
            "movie_title": movie["title"], "duration_min": movie["duration_min"],
            "theatre_name": theatre["name"], "screen_name": screen_name}
    seats = [{"seat_id": i, "row_label": SEATS[i]["row_label"], "seat_number": SEATS[i]["seat_number"],
              "seat_category": SEATS[i]["seat_category"], "price": _price(show_id, i)}
             for i in sorted(seat_ids) if i in SEATS]
    return show, seats, sum(seat["price"] for seat in seats)


def create_booking(customer_id, show_id, seat_ids, payment_method):
    """Raises ValueError with the same messages as services/booking_service.py."""
    s = SHOWS.get(show_id)
    if s is None:
        raise ValueError("Show not found")
    if datetime.combine(s["show_date"], s["start_time"]) <= datetime.now():
        raise ValueError("Show has already started")
    if any(SEATS.get(i, {}).get("screen_id") != s["screen_id"] for i in seat_ids):
        raise ValueError("One or more seats do not belong to this screen")
    taken = [i for i in seat_ids if i in TAKEN[show_id]]
    if taken:
        raise ValueError(f"Seat(s) {taken} already booked")
    booking_id = max(BOOKINGS, default=100) + 1
    now = datetime.now()
    BOOKINGS[booking_id] = {
        "booking_id": booking_id, "customer_id": customer_id, "show_id": show_id,
        "seat_ids": sorted(seat_ids), "status": "CONFIRMED", "booking_time": now,
        "total_amount": sum(_price(show_id, i) for i in seat_ids),
        "payment": {"payment_id": booking_id, "method": payment_method,
                    "status": "SUCCESS", "paid_at": now},
    }
    TAKEN[show_id].update(seat_ids)
    return {"booking_id": booking_id}


def get_confirmation(customer_id, booking_id):
    """Returns (booking, payment) like confirmation(), or None."""
    b = BOOKINGS.get(booking_id)
    if b is None or b["customer_id"] != customer_id:
        return None
    s, movie, theatre, screen_name, screen_type = _show_info(b["show_id"])
    booking = {
        "booking_id": booking_id, "booking_time": b["booking_time"],
        "total_amount": b["total_amount"], "status": b["status"], "show_id": b["show_id"],
        "show_date": s["show_date"], "start_time": s["start_time"], "end_time": s["end_time"],
        "movie_title": movie["title"], "duration_min": movie["duration_min"],
        "poster_url": movie["poster_url"], "theatre_name": theatre["name"],
        "city": theatre["city"], "address": theatre["address"],
        "screen_name": screen_name, "screen_type": screen_type,
        "seats": [_label(i) for i in b["seat_ids"]],
        "seat_categories": [SEATS[i]["seat_category"] for i in b["seat_ids"]],
        "prices": [_price(b["show_id"], i) for i in b["seat_ids"]],
    }
    payment = dict(b["payment"], amount=b["total_amount"])
    return booking, payment


def get_my_bookings(customer_id):
    result = []
    for b in sorted(BOOKINGS.values(), key=lambda b: b["booking_time"], reverse=True):
        if b["customer_id"] != customer_id:
            continue
        s, movie, theatre, screen_name, _ = _show_info(b["show_id"])
        result.append({
            "booking_id": b["booking_id"], "booking_time": b["booking_time"],
            "total_amount": b["total_amount"], "status": b["status"], "show_id": b["show_id"],
            "show_date": s["show_date"], "start_time": s["start_time"],
            "movie_title": movie["title"], "poster_url": movie["poster_url"],
            "theatre_name": theatre["name"], "screen_name": screen_name,
            "seats": [_label(i) for i in b["seat_ids"]],
            "payment_status": b["payment"]["status"],
        })
    return result


def cancel_booking(customer_id, booking_id):
    """Raises ValueError with the same messages as services/cancellation_service.py."""
    b = BOOKINGS.get(booking_id)
    if b is None:
        raise ValueError("Booking not found")
    if b["customer_id"] != customer_id:
        raise ValueError("Not authorized to cancel this booking")
    if b["status"] != "CONFIRMED":
        raise ValueError("Only confirmed bookings can be cancelled")
    s = SHOWS[b["show_id"]]
    if datetime.combine(s["show_date"], s["start_time"]) - datetime.now() < timedelta(hours=2):
        raise ValueError("Cannot cancel: show starts in less than 2 hours")
    b["status"] = "CANCELLED"
    b["payment"]["status"] = "REFUNDED"
    TAKEN[b["show_id"]].difference_update(b["seat_ids"])


def seed_sample_bookings(customer_id):
    """Gives a newly logged-in preview user three bookings to look at:
    one cancellable, one cancelled and refunded, one too close to cancel."""
    if any(b["customer_id"] == customer_id for b in BOOKINGS.values()):
        return
    future = [s for s in SHOWS.values() if s["show_date"] >= date.today() + timedelta(days=2)]
    soon = sorted(SHOWS.values(), key=lambda s: abs(
        datetime.combine(s["show_date"], s["start_time"]) - datetime.now() - timedelta(hours=1)))[0]
    picks = [(future[0], "CONFIRMED", "UPI", "SUCCESS"), (future[5], "CANCELLED", "CARD", "REFUNDED"),
             (soon, "CONFIRMED", "UPI", "SUCCESS")]
    for show, status, method, pay_status in picks:
        free = [i for i, seat in SEATS.items()
                if seat["screen_id"] == show["screen_id"] and i not in TAKEN[show["show_id"]]][:2]
        booking_id = max(BOOKINGS, default=100) + 1
        when = datetime.now() - timedelta(days=1)
        BOOKINGS[booking_id] = {
            "booking_id": booking_id, "customer_id": customer_id, "show_id": show["show_id"],
            "seat_ids": free, "status": status, "booking_time": when,
            "total_amount": sum(_price(show["show_id"], i) for i in free),
            "payment": {"payment_id": booking_id, "method": method, "status": pay_status, "paid_at": when},
        }
        if status == "CONFIRMED":
            TAKEN[show["show_id"]].update(free)
