# CineBook: Multiplex Movie Ticket Booking System — DBMS Project Report

**Course:** 25CS2004 — Database Systems Design  
**Institution:** Indian Institute of Information Technology, Design and Manufacturing (IIITDM), Kancheepuram  
**Submission Date:** November 2026

| Team Member | Role | Core Ownership |
| :--- | :--- | :--- |
| **Tharanesh R** | Backend & Database Engineer | PostgreSQL schema, constraints, triggers, atomic booking & cancellation transactions (`FOR UPDATE`), FastAPI routes & authentication |
| **Mohit** | Frontend Lead (Customer Experience) | Customer UI templates (browse, filters, interactive seat map, checkout, confirmation ticket, booking history) & route integration |
| **Yashvant A T K (ATK)** | Admin, Data, SQL Showcase & Documentation Lead | ER diagram, 3NF relational schema, realistic Indian multiplex seed data, 3 SQL views, 14 showcase queries, Admin & Reports UI, testing log, and final report |

## 1. Problem Statement and Objectives

### 1.1 Problem Statement
A modern multiplex operates multiple branches, several screens per branch (2D, 3D, IMAX), dozens of daily showtimes, and tiered seat categories (`REGULAR`, `PREMIUM`, `RECLINER`). When bookings are tracked manually or in loosely coupled spreadsheets/files:
1. **Race-Condition Double Bookings:** Two customers selecting the same seat simultaneously can both be issued tickets for that seat.
2. **Stale Availability & Blocked Cancellations:** Cancelled tickets fail to release seats back into live inventory immediately, or leave payment/refund records inconsistent.
3. **Lack of Real-Time Analytics:** Theatre managers cannot instantly query movie-wise revenue, screen occupancy percentages, unsold movies, or daily sales trends.

### 1.2 Why a Database-Backed Application Is Needed
A relational database management system (**PostgreSQL 16**) acts as the single trusted system of record for movies, screens, seats, shows, pricing, bookings, tickets, and payments. By enforcing domain constraints, foreign keys, row-level locks (`SELECT ... FOR UPDATE`), and a **partial unique index on active tickets** inside the database engine itself, double booking becomes physically impossible regardless of concurrent application traffic.

### 1.3 Project Objectives
1. Enable customers to browse and filter movies, view live seat availability per show, pick exact seats on a visual seat map, complete payment, and view or cancel their bookings.
2. Make double booking of a seat impossible through a PostgreSQL partial unique index combined with an atomic transaction and `FOR UPDATE` row locking.
3. Process ticket cancellations and refunds atomically (for shows more than 2 hours away) so cancelled seats immediately return to the available pool while historical records remain auditable.
4. Provide an Admin & Reports interface to manage catalog/shows and view live business analytics.
5. Demonstrate all core SQL concepts from the course (`SELECT/WHERE/ORDER BY`, `LIKE/ILIKE`, `COUNT/SUM/AVG/MIN/MAX`, `JOIN`s across 5+ tables, `LEFT JOIN`, `GROUP BY / HAVING`, correlated and non-correlated subqueries, `VIEW`s, triggers, stored functions, and `INSERT/UPDATE/DELETE`) powering real application features.

## 2. Description of the Application and Its Users

CineBook serves two user roles stored in a unified `Customer` table differentiated by a `role` attribute (`CHECK (role IN ('CUSTOMER', 'ADMIN'))`):
* **Customer:** Registers and logs in, searches and filters movies by title, genre, language, certificate (`U`, `UA`, `A`), and minimum rating, selects a showtime, picks up to 6 seats on an interactive color-coded seat map, pays via `UPI`, `CARD`, or `CASH`, views confirmation tickets, and cancels confirmed bookings more than 2 hours prior to showtime for an instant refund.
* **Admin / Theatre Manager:** Accesses the protected `/admin` dashboard and `/reports/*` suite to monitor aggregate ticket/revenue KPIs, movie-wise revenue, show occupancy percentages (including above-average occupancy filtering), top customers, 7-day daily sales, unsold movies, unbooked customers, and busiest screens.

## 3. Functional Modules

| # | Module | Functional Description | Database Tables / Views Used | Primary Owners |
| :--- | :--- | :--- | :--- | :--- |
| **1** | **Customer Management & Auth** | Registration, bcrypt password hashing, session/JWT login, role guard, booking history | `Customer` | Tharanesh (Backend), Mohit (UI) |
| **2** | **Movie & Genre Catalog** | Browse, search (`ILIKE`), and filter movies by genre, language, certificate, and rating; manage movie catalog | `Movie`, `Genre`, `Movie_Genre` | Tharanesh, ATK, Mohit |
| **3** | **Theatre & Screen Setup** | Multiplex branches across cities (Chennai, Bengaluru), screen formats (`2D`, `3D`, `IMAX`), and seat layouts (`REGULAR`, `PREMIUM`, `RECLINER`) | `Theatre`, `Screen`, `Seat` | Tharanesh, ATK |
| **4** | **Show Scheduling & Tiered Pricing** | Schedule movies on screens with non-overlapping time windows and per-show category pricing | `Show`, `Show_Pricing` | Tharanesh, ATK |
| **5** | **Seat Selection & Atomic Booking** | Live seat map rendering (`available` vs `taken`) and atomic multi-seat booking with `FOR UPDATE` locking | `Show`, `Seat`, `Show_Pricing`, `Booking`, `Ticket` | Tharanesh, Mohit |
| **6** | **Payment Recording** | Record payment (`UPI`, `CARD`, `CASH`) inside the booking transaction and snapshot prices | `Payment`, `Booking` | Tharanesh, Mohit |
| **7** | **Cancellation & Refund** | Verify `> 2 hours` cutoff, mark booking & tickets `CANCELLED`, mark payment `REFUNDED`, and free seats | `Booking`, `Ticket`, `Payment` | Tharanesh, Mohit |
| **8** | **Search, Views & Analytics Reports** | Live KPI cards, revenue by movie, show occupancy, top customers, daily sales, unsold movies, busiest screens | `show_availability`, `booking_summary`, `revenue_report` (over all 12 tables) | ATK (SQL & Reports), Tharanesh (Routes) |

## 4. Entity-Relationship (ER) Diagram & Cardinalities



*(Full Mermaid diagram and `dbdiagram.io` DBML source are also maintained in `docs/database_design_and_er.md`.)*

| Relationship | Cardinality | Foreign Key / Junction Implementation | Referential Action |
| :--- | :--- | :--- | :--- |
| **Theatre has Screens** | `1 : N` | `Screen.theatre_id` → `Theatre.theatre_id` | `ON DELETE CASCADE` |
| **Screen has Seats** | `1 : N` | `Seat.screen_id` → `Screen.screen_id` | `ON DELETE CASCADE` |
| **Screen hosts Shows** | `1 : N` | `Show.screen_id` → `Screen.screen_id` | `ON DELETE CASCADE` |
| **Movie is played in Shows** | `1 : N` | `Show.movie_id` → `Movie.movie_id` | `ON DELETE RESTRICT` |
| **Movie has Genres** | `M : N` | `Movie_Genre(movie_id, genre_id)` | `ON DELETE CASCADE` |
| **Show has Category Prices** | `1 : N` | `Show_Pricing.show_id` → `Show.show_id` | `ON DELETE CASCADE` |
| **Customer makes Bookings** | `1 : N` | `Booking.customer_id` → `Customer.customer_id` | `ON DELETE RESTRICT` |
| **Show receives Bookings** | `1 : N` | `Booking.show_id` → `Show.show_id` | `ON DELETE RESTRICT` |
| **Booking contains Tickets** | `1 : N` | `Ticket.booking_id` → `Booking.booking_id` | `ON DELETE CASCADE` |
| **Seat appears on Tickets** | `1 : N` | `Ticket.seat_id` → `Seat.seat_id` | `ON DELETE RESTRICT` |
| **Booking has Payments** | `1 : N` | `Payment.booking_id` → `Booking.booking_id` | `ON DELETE CASCADE` |

## 5. Relational Schema with Keys and Constraints (12 Tables)

| # | Table Name | Primary Key (PK) | Foreign Keys (FK) | Key Constraints & Indexes |
| :--- | :--- | :--- | :--- | :--- |
| **1** | `Customer` | `customer_id` (`SERIAL`) | — | `name, email, phone NOT NULL`; `email UNIQUE`; `phone UNIQUE`; `role CHECK IN ('CUSTOMER', 'ADMIN')` |
| **2** | `Movie` | `movie_id` (`SERIAL`) | — | `title NOT NULL`; `duration_min CHECK (> 0)`; `certificate CHECK IN ('U', 'UA', 'A')`; `rating CHECK (0..10)` |
| **3** | `Genre` | `genre_id` (`SERIAL`) | — | `genre_name UNIQUE NOT NULL` |
| **4** | `Movie_Genre` | `(movie_id, genre_id)` | `movie_id` → `Movie`<br>`genre_id` → `Genre` | Composite PK; `ON DELETE CASCADE` on both FKs |
| **5** | `Theatre` | `theatre_id` (`SERIAL`) | — | `name, city, address NOT NULL` |
| **6** | `Screen` | `screen_id` (`SERIAL`) | `theatre_id` → `Theatre` | `UNIQUE (theatre_id, screen_name)`; `screen_type CHECK IN ('2D', '3D', 'IMAX')` |
| **7** | `Seat` | `seat_id` (`SERIAL`) | `screen_id` → `Screen` | `UNIQUE (screen_id, row_label, seat_number)`; `seat_category CHECK IN ('REGULAR', 'PREMIUM', 'RECLINER')` |
| **8** | `Show` | `show_id` (`SERIAL`) | `movie_id` → `Movie`<br>`screen_id` → `Screen` | `UNIQUE (screen_id, show_date, start_time)`; `CHECK (end_time > start_time)`; `trg_prevent_show_overlap` trigger |
| **9** | `Show_Pricing` | `(show_id, seat_category)` | `show_id` → `Show` | Composite PK; `seat_category CHECK IN ('REGULAR', 'PREMIUM', 'RECLINER')`; `price CHECK (>= 0)` |
| **10** | `Booking` | `booking_id` (`SERIAL`) | `customer_id` → `Customer`<br>`show_id` → `Show` | `total_amount CHECK (>= 0)`; `status CHECK IN ('PENDING', 'CONFIRMED', 'CANCELLED')` |
| **11** | `Ticket` | `ticket_id` (`SERIAL`) | `booking_id` → `Booking`<br>`show_id` → `Show`<br>`seat_id` → `Seat` | `price CHECK (>= 0)`; `status CHECK IN ('ACTIVE', 'CANCELLED')`; **Partial Unique Index:** `UNIQUE (show_id, seat_id) WHERE status = 'ACTIVE'` |
| **12** | `Payment` | `payment_id` (`SERIAL`) | `booking_id` → `Booking` | `amount CHECK (> 0)`; `method CHECK IN ('UPI', 'CARD', 'CASH')`; `status CHECK IN ('SUCCESS', 'FAILED', 'REFUNDED')` |

## 6. Normalization Argument & Key Design Decisions

1. **First Normal Form (1NF):** Every column in all 12 tables holds an atomic scalar value. Multi-valued movie genres are decomposed into `Genre` and `Movie_Genre(movie_id, genre_id)`, and multi-seat bookings are decomposed into individual `Ticket` rows.
2. **Second Normal Form (2NF):** Every non-key attribute in composite-key tables (`Movie_Genre` and `Show_Pricing`) depends on the **whole** composite key. In `Show_Pricing(show_id, seat_category)`, `price` depends on both the specific show (weekday vs. weekend, 2D vs. IMAX) and the seat category (`REGULAR`, `PREMIUM`, `RECLINER`).
3. **Third Normal Form (3NF):** No transitive dependencies exist. Theatre city/address live solely in `Theatre`, screen format lives solely in `Screen`, movie attributes live solely in `Movie`, and customer details live solely in `Customer`.
4. **Deliberate Design Exceptions (Justified in Course Brief):**
   - **Historical Price Snapshots (`Ticket.price` and `Booking.total_amount`):** Show prices in `Show_Pricing` can be modified by an admin over time, but a past booking receipt and refund must reflect what the customer was actually charged at booking time.
   - **Database-Enforced Double-Booking Prevention (`idx_ticket_active_seat`):** Storing `show_id` on `Ticket` enables the partial unique index `CREATE UNIQUE INDEX idx_ticket_active_seat ON Ticket (show_id, seat_id) WHERE status = 'ACTIVE'`. Cancelled tickets (`status = 'CANCELLED'`) remain in the table for audit history without blocking the seat from being re-booked by the next customer.
   - **Zero Stored Derivable Columns:** Screen capacity, booked seat counts, seats remaining, and occupancy percentages are computed dynamically via SQL views (`show_availability`, `booking_summary`, `revenue_report`).

## 7. Important SQL Commands (DDL, Constraints, Triggers & DML)

### 7.1 Partial Unique Index Stopping Double Booking (`db/schema.sql`)
```sql
CREATE UNIQUE INDEX IF NOT EXISTS idx_ticket_active_seat
    ON Ticket (show_id, seat_id)
    WHERE status = 'ACTIVE';
```

### 7.2 Trigger Blocking Overlapping Shows on One Screen (`db/schema.sql`)
```sql
CREATE OR REPLACE FUNCTION fn_prevent_show_overlap()
RETURNS TRIGGER AS $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM Show s
        WHERE s.screen_id = NEW.screen_id
          AND s.show_date = NEW.show_date
          AND s.show_id <> COALESCE(NEW.show_id, -1)
          AND NEW.start_time < s.end_time
          AND NEW.end_time > s.start_time
    ) THEN
        RAISE EXCEPTION 'Overlapping show on screen % on % between % and %',
            NEW.screen_id, NEW.show_date, NEW.start_time, NEW.end_time
            USING ERRCODE = '23505';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### 7.3 Data-Changing Operations (`INSERT`, `UPDATE`, `DELETE` & Foreign Key Block)
Full runnable examples are included in **Part D of `db/queries.sql`**, demonstrating:
* **`INSERT`:** Registering a customer, adding a movie, scheduling a show, and inserting a booking with tickets and payment.
* **`UPDATE`:** Updating movie ratings, adjusting show category prices in `Show_Pricing`, and cancelling a booking (`Booking.status = 'CANCELLED'`, `Ticket.status = 'CANCELLED'`, `Payment.status = 'REFUNDED'`).
* **`DELETE`:** Deleting a movie without scheduled shows succeeds, whereas attempting `DELETE FROM Movie WHERE movie_id = 1` (*Leo*) is refused by PostgreSQL's `ON DELETE RESTRICT` foreign key on `Show.movie_id`.

## 8. The 14 Graded SQL Queries and 3 Views (`db/queries.sql` & `db/views.sql`)

All 14 queries and 3 views are implemented and documented in `db/queries.sql` and `db/views.sql`:
1. **Query #1 (`SELECT, WHERE, ORDER BY`):** Shows for Movie #1 (*Leo*) on a chosen date, earliest first (`Show picker`).
2. **Query #2 (`WHERE` with `AND/OR`, `LIKE`):** Movies filtered by language (`Tamil`/`English`), certificate (`U`/`UA`), and rating $\ge 8.0$ (`Movie list search`).
3. **Query #3 (`COUNT, SUM, AVG, MIN, MAX`):** Total tickets sold (`76`), total revenue (`₹23,070`), average (`₹303.55`), highest (`₹530`), and lowest (`₹150`) ticket price (`Admin dashboard KPI cards`).
4. **Query #4 (`JOIN, GROUP BY, SUM`):** Revenue and tickets sold per movie (`Revenue report`).
5. **Query #5 (`GROUP BY` with `HAVING`):** Top movies whose revenue crosses `₹2,000` (`Top movies report`).
6. **Query #6 (8-table `JOIN`):** Full booking details joining `Booking`, `Customer`, `Show`, `Movie`, `Screen`, `Theatre`, `Ticket`, `Seat`, and `Payment` (`Confirmation & My Bookings`).
7. **Query #7 (`LEFT JOIN`):** All 10 movies including *Kanguva* (`scheduled_shows_count = 0`).
8. **Query #8 (`NOT EXISTS` Subquery):** Customers who have never booked (*Meera Krishnan*, *Test Customer*).
9. **Query #9 (`NOT IN` Subquery):** Movies with zero scheduled shows (*Kanguva*).
10. **Query #10 (Subquery with `AVG` Aggregate):** Shows whose occupancy % exceeds the overall average occupancy (`Occupancy report filter`).
11. **Query #11 (`GROUP BY, ORDER BY, LIMIT`):** Top 10 customers ranked by total money spent (`Top customers report`).
12. **Query #12 (`GROUP BY` on Date):** Daily bookings and revenue over the last 7 days (`Daily sales report`).
13. **Query #13 (Subquery Excluding Active Tickets):** Available seats and tier prices for a show (`Seat map`).
14. **Query #14 (Aggregate over `JOIN`s):** Busiest theatre and screen ranked by tickets sold (`Busiest screens report`).
* **3 Views (`db/views.sql`):** `show_availability`, `booking_summary`, and `revenue_report`.

### 8.1 SQL Query & View Output Screenshots (`psql -f db/queries.sql`)









## 9. How the Application Talks to the Database (Architecture & Transactions)

* **Connection Pooling (`backend/database.py`):** Uses `psycopg_pool.ConnectionPool` (`min_size=2, max_size=10`) with a `@contextmanager def get_db()` generator that yields a cursor inside a managed connection transaction—automatically committing on normal exit and rolling back on any unhandled exception.
* **Atomic Booking Transaction (`backend/services/booking_service.py`):**
  1. Verifies the show exists and has not started (`show_datetime > datetime.now()`).
  2. Verifies all requested `seat_id`s belong to the show's `screen_id`.
  3. Locks the selected `Seat` rows with `SELECT ... FOR UPDATE`.
  4. Checks `Ticket` (`FOR SHARE`) to ensure none of the selected seats has an `ACTIVE` ticket for `show_id`.
  5. Looks up tier prices from `Show_Pricing` and computes the total.
  6. Inserts `Booking` (`PENDING`), inserts one `Ticket` (`ACTIVE`) per seat with its snapshot `price`, inserts `Payment` (`SUCCESS`), updates `Booking` to `CONFIRMED`, and commits atomically.
* **Atomic Cancellation Transaction (`backend/services/cancellation_service.py`):**
  1. Verifies the booking belongs to the logged-in customer, is `CONFIRMED`, and the show starts more than 2 hours in the future (`show_datetime > datetime.now() + timedelta(hours=2)`).
  2. Atomically updates `Booking.status = 'CANCELLED'`, `Ticket.status = 'CANCELLED'`, and `Payment.status = 'REFUNDED'`.

## 10. Application Screenshots











## 11. Results, Observations, and Future Enhancements

* **What Worked Well:** Enforcing seat uniqueness via a PostgreSQL partial unique index (`WHERE status = 'ACTIVE'`) combined with `FOR UPDATE` row locking eliminated race-condition double bookings completely while allowing cancelled seats to be re-booked seamlessly. Using relative `CURRENT_DATE` offsets in `db/seed.sql` ensured perennial test and demo data.
* **What Constraints Caught:** Database `CHECK` constraints caught invalid ratings, negative prices, and invalid certificates; `ON DELETE RESTRICT` prevented accidental deletion of movies with scheduled shows; and `trg_prevent_show_overlap` prevented scheduling colliding showtimes on the same screen.
* **Future Enhancements:** Adding temporary 5-minute seat holds (`PENDING` bookings with expiry cleanup), real payment gateway webhook integration (Razorpay/Stripe), and dynamic QR codes on confirmation tickets.
