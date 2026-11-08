"""
Admin service - add / edit / delete movies, add theatres and screens,
schedule shows and set their category prices.

Every function takes a cursor from get_db(), so each route runs as one
transaction: it commits when the `with get_db()` block ends and rolls back
if anything raises. ValueError carries a message that is safe to show.
"""

from datetime import date, datetime, time, timedelta
from string import ascii_uppercase

CERTIFICATES = ("U", "UA", "A")
SCREEN_TYPES = ("2D", "3D", "IMAX")
SEAT_CATEGORIES = ("REGULAR", "PREMIUM", "RECLINER")


# ===== MOVIES =====

def list_movies(cur):
    """All movies with their genres and how many shows each has."""
    cur.execute("""
        SELECT m.movie_id, m.title, m.language, m.certificate, m.duration_min,
               m.release_date, m.rating,
               COALESCE(STRING_AGG(DISTINCT g.genre_name, ', '), '') AS genres,
               COUNT(DISTINCT sh.show_id) AS show_count
        FROM Movie m
        LEFT JOIN Movie_Genre mg ON mg.movie_id = m.movie_id
        LEFT JOIN Genre g ON g.genre_id = mg.genre_id
        LEFT JOIN Show sh ON sh.movie_id = m.movie_id
        GROUP BY m.movie_id
        ORDER BY m.title
    """)
    return [{
        "movie_id": r[0], "title": r[1], "language": r[2], "certificate": r[3],
        "duration_min": r[4], "release_date": r[5], "rating": r[6],
        "genres": r[7], "show_count": r[8]
    } for r in cur.fetchall()]


def list_genres(cur):
    cur.execute("SELECT genre_id, genre_name FROM Genre ORDER BY genre_name")
    return [{"genre_id": r[0], "genre_name": r[1]} for r in cur.fetchall()]


def get_movie(cur, movie_id: int):
    cur.execute("""
        SELECT movie_id, title, description, duration_min, language, certificate,
               release_date, rating, poster_url
        FROM Movie WHERE movie_id = %s
    """, (movie_id,))
    r = cur.fetchone()
    if not r:
        return None
    cur.execute("SELECT genre_id FROM Movie_Genre WHERE movie_id = %s", (movie_id,))
    return {
        "movie_id": r[0], "title": r[1], "description": r[2] or "", "duration_min": r[3],
        "language": r[4], "certificate": r[5], "release_date": r[6],
        "rating": r[7] if r[7] is not None else "", "poster_url": r[8] or "",
        "genre_ids": [row[0] for row in cur.fetchall()]
    }


def parse_movie_form(form):
    """Check the movie form. Returns (movie dict, list of error messages)."""
    errors = []
    movie = {
        "title": (form.get("title") or "").strip(),
        "description": (form.get("description") or "").strip(),
        "language": (form.get("language") or "").strip(),
        "certificate": form.get("certificate") or "",
        "poster_url": (form.get("poster_url") or "").strip(),
        "duration_min": (form.get("duration_min") or "").strip(),
        "release_date": (form.get("release_date") or "").strip(),
        "rating": (form.get("rating") or "").strip(),
        "genre_ids": [int(g) for g in form.getlist("genre_ids") if g.isdigit()],
    }

    if not movie["title"] or len(movie["title"]) > 200:
        errors.append("Title is required (up to 200 characters).")
    if not movie["language"]:
        errors.append("Language is required.")
    if movie["certificate"] not in CERTIFICATES:
        errors.append("Certificate must be U, UA or A.")
    if movie["poster_url"] and not movie["poster_url"].startswith(("http://", "https://")):
        errors.append("Poster URL must start with http:// or https://.")

    if movie["duration_min"].isdigit() and int(movie["duration_min"]) > 0:
        movie["duration_min"] = int(movie["duration_min"])
    else:
        errors.append("Duration must be a whole number of minutes above 0.")

    try:
        movie["release_date"] = date.fromisoformat(movie["release_date"])
    except ValueError:
        errors.append("Release date is required.")

    if movie["rating"]:
        try:
            movie["rating"] = round(float(movie["rating"]), 1)
            if not 0 <= movie["rating"] <= 10:
                raise ValueError
        except ValueError:
            errors.append("Rating must be between 0 and 10.")
    else:
        movie["rating"] = None

    return movie, errors


def _save_genres(cur, movie_id: int, genre_ids: list):
    cur.execute("DELETE FROM Movie_Genre WHERE movie_id = %s", (movie_id,))
    cur.executemany(
        "INSERT INTO Movie_Genre (movie_id, genre_id) VALUES (%s, %s)",
        [(movie_id, g) for g in genre_ids],
    )


def create_movie(cur, movie: dict) -> int:
    cur.execute("""
        INSERT INTO Movie (title, description, duration_min, language, certificate,
                           release_date, rating, poster_url)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING movie_id
    """, (movie["title"], movie["description"] or None, movie["duration_min"],
          movie["language"], movie["certificate"], movie["release_date"],
          movie["rating"], movie["poster_url"] or None))
    movie_id = cur.fetchone()[0]
    _save_genres(cur, movie_id, movie["genre_ids"])
    return movie_id


def update_movie(cur, movie_id: int, movie: dict):
    cur.execute("""
        UPDATE Movie
        SET title = %s, description = %s, duration_min = %s, language = %s,
            certificate = %s, release_date = %s, rating = %s, poster_url = %s
        WHERE movie_id = %s
    """, (movie["title"], movie["description"] or None, movie["duration_min"],
          movie["language"], movie["certificate"], movie["release_date"],
          movie["rating"], movie["poster_url"] or None, movie_id))
    if cur.rowcount == 0:
        raise ValueError("Movie not found")
    _save_genres(cur, movie_id, movie["genre_ids"])


def delete_movie(cur, movie_id: int) -> str:
    """Delete a movie. Show.movie_id is ON DELETE RESTRICT, so PostgreSQL itself
    refuses (ForeignKeyViolation) when the movie has shows; the caller reports it."""
    cur.execute("DELETE FROM Movie WHERE movie_id = %s RETURNING title", (movie_id,))
    row = cur.fetchone()
    if not row:
        raise ValueError("Movie not found")
    return row[0]


# ===== THEATRES & SCREENS =====

def list_theatres(cur):
    """Theatres with their screens and seat counts per category."""
    cur.execute("SELECT theatre_id, name, city, address FROM Theatre ORDER BY city, name")
    theatres = [{"theatre_id": r[0], "name": r[1], "city": r[2], "address": r[3], "screens": []}
                for r in cur.fetchall()]
    by_id = {t["theatre_id"]: t for t in theatres}
    cur.execute("""
        SELECT sc.theatre_id, sc.screen_id, sc.screen_name, sc.screen_type,
               COUNT(st.seat_id) AS seats,
               COUNT(st.seat_id) FILTER (WHERE st.seat_category = 'REGULAR') AS regular,
               COUNT(st.seat_id) FILTER (WHERE st.seat_category = 'PREMIUM') AS premium,
               COUNT(st.seat_id) FILTER (WHERE st.seat_category = 'RECLINER') AS recliner
        FROM Screen sc
        LEFT JOIN Seat st ON st.screen_id = sc.screen_id
        GROUP BY sc.screen_id
        ORDER BY sc.screen_name
    """)
    for r in cur.fetchall():
        by_id[r[0]]["screens"].append({
            "screen_id": r[1], "screen_name": r[2], "screen_type": r[3],
            "seats": r[4], "regular": r[5], "premium": r[6], "recliner": r[7]
        })
    return theatres


def create_theatre(cur, name: str, city: str, address: str) -> int:
    if not name or not city or not address:
        raise ValueError("Name, city and address are all required.")
    cur.execute("""
        INSERT INTO Theatre (name, city, address) VALUES (%s, %s, %s)
        RETURNING theatre_id
    """, (name, city, address))
    return cur.fetchone()[0]


def create_screen(cur, theatre_id: int, screen_name: str, screen_type: str,
                  row_count: int, seats_per_row: int, premium_rows: int, recliner_rows: int) -> dict:
    """Add a screen and generate its seats: front rows REGULAR, then PREMIUM,
    back rows RECLINER. Rows are lettered A, B, C... from the screen."""
    if not screen_name:
        raise ValueError("Screen name is required.")
    if screen_type not in SCREEN_TYPES:
        raise ValueError("Screen type must be 2D, 3D or IMAX.")
    if not 1 <= row_count <= 26:
        raise ValueError("Rows must be between 1 and 26.")
    if not 1 <= seats_per_row <= 40:
        raise ValueError("Seats per row must be between 1 and 40.")
    if premium_rows < 0 or recliner_rows < 0 or premium_rows + recliner_rows > row_count:
        raise ValueError("Premium and recliner rows can't add up to more than the total rows.")

    cur.execute("""
        INSERT INTO Screen (theatre_id, screen_name, screen_type) VALUES (%s, %s, %s)
        RETURNING screen_id
    """, (theatre_id, screen_name, screen_type))
    screen_id = cur.fetchone()[0]

    regular_rows = row_count - premium_rows - recliner_rows
    seats = []
    for i, row_label in enumerate(ascii_uppercase[:row_count]):
        if i < regular_rows:
            category = "REGULAR"
        elif i < regular_rows + premium_rows:
            category = "PREMIUM"
        else:
            category = "RECLINER"
        seats += [(screen_id, row_label, n, category) for n in range(1, seats_per_row + 1)]
    cur.executemany("""
        INSERT INTO Seat (screen_id, row_label, seat_number, seat_category)
        VALUES (%s, %s, %s, %s)
    """, seats)
    return {"screen_id": screen_id, "seats_created": len(seats)}


# ===== SHOWS & PRICING =====

def list_screens(cur):
    """Every screen with its theatre, for the schedule form."""
    cur.execute("""
        SELECT sc.screen_id, th.name, th.city, sc.screen_name, sc.screen_type
        FROM Screen sc JOIN Theatre th ON th.theatre_id = sc.theatre_id
        ORDER BY th.city, th.name, sc.screen_name
    """)
    return [{"screen_id": r[0], "label": f"{r[1]} ({r[2]}) · {r[3]} · {r[4]}"} for r in cur.fetchall()]


def list_upcoming_shows(cur):
    """Shows from today onwards with their three category prices and seats sold."""
    cur.execute("""
        SELECT sh.show_id, sh.show_date, sh.start_time, sh.end_time,
               m.title, th.name, sc.screen_name, sc.screen_type,
               MAX(sp.price) FILTER (WHERE sp.seat_category = 'REGULAR')  AS regular,
               MAX(sp.price) FILTER (WHERE sp.seat_category = 'PREMIUM')  AS premium,
               MAX(sp.price) FILTER (WHERE sp.seat_category = 'RECLINER') AS recliner,
               (SELECT COUNT(*) FROM Ticket t
                WHERE t.show_id = sh.show_id AND t.status = 'ACTIVE') AS sold
        FROM Show sh
        JOIN Movie m ON m.movie_id = sh.movie_id
        JOIN Screen sc ON sc.screen_id = sh.screen_id
        JOIN Theatre th ON th.theatre_id = sc.theatre_id
        LEFT JOIN Show_Pricing sp ON sp.show_id = sh.show_id
        WHERE sh.show_date >= CURRENT_DATE
        GROUP BY sh.show_id, m.title, th.name, sc.screen_name, sc.screen_type
        ORDER BY sh.show_date, sh.start_time, th.name
    """)
    return [{
        "show_id": r[0], "show_date": r[1], "start_time": r[2], "end_time": r[3],
        "movie_title": r[4], "theatre_name": r[5], "screen_name": r[6], "screen_type": r[7],
        "prices": {"REGULAR": r[8], "PREMIUM": r[9], "RECLINER": r[10]}, "sold": r[11]
    } for r in cur.fetchall()]


def parse_prices(form) -> dict:
    prices = {}
    for category in SEAT_CATEGORIES:
        value = (form.get(f"price_{category}") or "").strip()
        if not value.isdigit():
            raise ValueError(f"Enter a {category.title()} price in whole rupees (0 or more).")
        prices[category] = int(value)
    return prices


def _save_prices(cur, show_id: int, prices: dict):
    # Upsert keeps the (show_id, seat_category) primary key: one price per category per show
    cur.executemany("""
        INSERT INTO Show_Pricing (show_id, seat_category, price) VALUES (%s, %s, %s)
        ON CONFLICT (show_id, seat_category) DO UPDATE SET price = EXCLUDED.price
    """, [(show_id, category, price) for category, price in prices.items()])


def create_show(cur, movie_id: int, screen_id: int, show_date: date,
                start: time, end: time | None, prices: dict) -> int:
    """Schedule a show and its three prices in one transaction.

    If no end time is given it is start + movie duration. The screen row is
    locked first so two admins can't schedule overlapping shows on it at once.
    """
    if show_date < date.today():
        raise ValueError("Shows can't be scheduled in the past.")

    cur.execute("SELECT duration_min, title FROM Movie WHERE movie_id = %s", (movie_id,))
    movie = cur.fetchone()
    if not movie:
        raise ValueError("Movie not found.")

    cur.execute("SELECT screen_id FROM Screen WHERE screen_id = %s FOR UPDATE", (screen_id,))
    if not cur.fetchone():
        raise ValueError("Screen not found.")

    if end is None:
        end_dt = datetime.combine(show_date, start) + timedelta(minutes=movie[0])
        if end_dt.date() != show_date:
            raise ValueError("This show would run past midnight. Pick an earlier start time.")
        end = end_dt.time()
    if end <= start:
        raise ValueError("End time must be after the start time (shows can't run past midnight).")

    # Same overlap test as trg_prevent_show_overlap, checked here so the admin gets a clear message
    cur.execute("""
        SELECT m.title, sh.start_time, sh.end_time
        FROM Show sh JOIN Movie m ON m.movie_id = sh.movie_id
        WHERE sh.screen_id = %s AND sh.show_date = %s
          AND %s < sh.end_time AND %s > sh.start_time
        LIMIT 1
    """, (screen_id, show_date, start, end))
    clash = cur.fetchone()
    if clash:
        raise ValueError(f"That screen already has {clash[0]} from "
                         f"{clash[1].strftime('%H:%M')} to {clash[2].strftime('%H:%M')} on that day.")

    cur.execute("""
        INSERT INTO Show (movie_id, screen_id, show_date, start_time, end_time)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING show_id
    """, (movie_id, screen_id, show_date, start, end))
    show_id = cur.fetchone()[0]
    _save_prices(cur, show_id, prices)
    return show_id


def update_show_prices(cur, show_id: int, prices: dict):
    """Change a show's prices. Tickets already sold keep the price they were sold at
    (Ticket.price is a snapshot), so only new bookings see the new prices."""
    cur.execute("SELECT 1 FROM Show WHERE show_id = %s", (show_id,))
    if not cur.fetchone():
        raise ValueError("Show not found.")
    _save_prices(cur, show_id, prices)
