# CineBook: Multiplex Movie Booking System

CineBook is a movie ticket booking system for a multiplex chain with theatres in
Chennai and Bengaluru. Customers browse movies, pick a show, choose seats on a
live seat map, pay, and manage their bookings. Admins see sales and occupancy
reports built on SQL views and queries.

It was built as a DBMS course project, so the focus is on the database: a
normalised PostgreSQL schema (3NF, 12 tables), transactions with row locking
for seat booking, views, triggers, a stored function, and a set of graded SQL
queries. The web interface is deliberately simple and exists to show the
database at work.

## Features

**Customers**
- Register and log in (passwords are hashed with bcrypt; sessions use a signed cookie)
- Browse movies with search and filters for genre, language, certificate and rating
- See showtimes grouped by date and theatre, with seats left for each show
- Pick up to 6 seats on a seat map with Regular, Premium and Recliner sections
- Pay by UPI, card or cash at checkout and get a ticket-style confirmation
- See all bookings, and cancel one up to 2 hours before the show for a full refund

**Admins**
- Dashboard with tickets sold, revenue and average, highest and lowest ticket price
- Reports: revenue by movie, show occupancy, top customers, daily sales, movies
  with no shows, customers who never booked, busiest screens

**Database**
- Booking runs as one transaction: seats are locked with `SELECT ... FOR UPDATE`,
  so two people can't book the same seat at the same time
- Prices come from a per-show price table, so weekends and IMAX can cost more
- 3 views, 14 graded queries, 2 triggers (no overlapping shows on a screen,
  booking totals kept in sync with tickets), a `get_seats_left()` function and
  an index with an `EXPLAIN` comparison

## Tech stack

| Layer | Technology |
|-------|------------|
| Database | PostgreSQL 16 |
| Backend | Python, FastAPI, psycopg 3 (raw SQL, no ORM) |
| Pages | Jinja2 templates rendered on the server |
| Styling | Bootstrap 5 (from a CDN) and one stylesheet; small plain JavaScript files |

There is no frontend build step: no npm, no bundler.

## Project structure

```
backend/
  main.py                 FastAPI app: page routes, admin reports, error handlers
  auth.py                 Password hashing and login helpers
  database.py             PostgreSQL connection pool
  requirements.txt
  .env.example            Settings to copy into .env
  services/
    booking_service.py        Booking transaction (seat locking, tickets, payment)
    cancellation_service.py   Cancellation and refund transaction
    report_service.py         Admin report queries
  schemas/                Pydantic models for the planned JSON API
  app/
    templates/            Jinja pages (customer pages, admin pages, 404, error)
    static/css, static/js Stylesheet, seat picker and form helpers
    preview.py            Runs the customer pages with fake data, no database needed
    mock_data.py          Fake data used by preview.py
db/
  seed.sql                Creates all 12 tables and loads sample data
  views.sql               show_availability, booking_summary, revenue_report
  queries.sql             The 14 graded queries, triggers, function, index, DML demos
docs/
  database_design_and_er.md   ER diagram, relational schema, normalisation
  er_diagram.png
  api_contract.md             Design for a JSON API (not built yet)
```

## Getting started

### Requirements
- Python 3.10 or newer
- PostgreSQL 16 (local install or Docker)

### 1. Create and load the database

Create a database called `cinebook`, then load the schema, sample data and views:

```bash
createdb -U postgres cinebook
psql -U postgres -d cinebook -f db/seed.sql
psql -U postgres -d cinebook -f db/views.sql
```

`seed.sql` drops and recreates all the data, so you can run it again at any
time to reset. Show dates are relative to today, so there are always upcoming
shows to book.

To run the graded queries and create the triggers, function and index:

```bash
psql -P pager=off -U postgres -d cinebook -f db/queries.sql
```

Its INSERT, UPDATE and DELETE demos run inside a transaction that is rolled
back, so the sample data is not changed.

<details>
<summary>No PostgreSQL installed? Use Docker</summary>

```bash
docker run -d --name cinebook-db -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=cinebook -p 5432:5432 postgres:16
docker exec -i cinebook-db psql -U postgres -d cinebook < db/seed.sql
docker exec -i cinebook-db psql -U postgres -d cinebook < db/views.sql
```

Then use `postgresql://postgres:postgres@localhost:5432/cinebook` as the
`DATABASE_URL` below.
</details>

### 2. Install and configure the backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS / Linux
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set `DATABASE_URL` to your database, for example:

```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/cinebook
JWT_SECRET=change-this-to-a-long-random-string
```

`JWT_SECRET` also signs the login session cookie, so use your own value.

### 3. Run the app

From the `backend` folder:

```bash
uvicorn main:app --reload
```

Open http://localhost:8000.

### Sample accounts

Every sample account uses the password `password123`.

| Email | Role | Notes |
|-------|------|-------|
| `admin@cinebook.in` | Admin | Opens the dashboard at `/admin` |
| `tharanesh@cinebook.in` | Customer | Has past and upcoming bookings |
| `mohit@cinebook.in` | Customer | Has past and upcoming bookings |
| `meera.krishnan@gmail.com` | Customer | Has never booked |

## Trying the booking flow

1. Open **Movies**, search or filter, and pick a movie.
2. Choose a date and a showtime. Each show lists the seats left.
3. Log in when asked, then pick up to 6 seats. Taken seats are greyed out.
4. At checkout choose UPI, card or cash and pay.
5. The confirmation page shows the ticket. **My Bookings** lists it, with a
   Cancel button until 2 hours before the show.

Booking the same seat from two browsers at once shows how the locking works:
the second person gets a "Seat(s) ... already booked" message.

## Previewing pages without a database

To work on the page design without PostgreSQL, run the preview server. It
serves the customer pages with fake data and accepts any email and password:

```bash
cd backend
python app/preview.py
```

Open http://127.0.0.1:8001. It needs only `fastapi`, `uvicorn`, `jinja2`,
`python-multipart` and `itsdangerous`. The admin pages need the real app.

## Database design

The schema has 12 tables in Third Normal Form: `Customer`, `Movie`, `Genre`,
`Movie_Genre`, `Theatre`, `Screen`, `Seat`, `Show`, `Show_Pricing`, `Booking`,
`Ticket` and `Payment`. The ER diagram, the relational schema, relationships
and the normalisation write-up are in
[docs/database_design_and_er.md](docs/database_design_and_er.md).

![ER diagram](docs/er_diagram.png)

## Team

| Member | Responsibility |
|--------|----------------|
| Tharanesh | Backend: FastAPI routes, booking and cancellation transactions |
| Mohit | Frontend: customer pages, seat picker, styling |
| Yashvant A T K | Database: schema, seed data, views, queries, documentation |
