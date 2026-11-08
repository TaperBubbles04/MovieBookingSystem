# CineBook — 10-Minute Demo Script & Viva Preparation Guide

**Project:** CineBook — Multiplex Booking System (`25CS2004 Database Systems Design`)  
**Team:** Tharanesh (Backend & DB), Mohit (Customer UI), Yashvant A T K / ATK (Admin, Data, SQL Showcase & Docs)

## 1. Pre-Demo Setup Checklist (5 Minutes Before Presentation)

1. Reset and seed the database so all 12 tables and relative show dates are fresh:
   ```powershell
   psql -U postgres -d cinebook -f db/schema.sql
   psql -U postgres -d cinebook -f db/seed.sql
   psql -U postgres -d cinebook -f db/views.sql
   ```
2. Start the FastAPI server:
   ```powershell
   cd backend
   python main.py
   ```
3. Open **two browser windows** side-by-side:
   - **Browser 1 (Normal Window):** Logged in as Customer (`tharanesh@cinebook.in` / `password123`), with a second tab ready for Admin (`admin@cinebook.in` / `password123`).
   - **Browser 2 (Incognito Window):** Logged in as Customer (`mohit@cinebook.in` / `password123`) for the live double-booking concurrency test.
4. Keep a terminal tab open in the project root ready to run `psql -P pager=off -U postgres -d cinebook -f db/queries.sql`.

## 2. Minute-by-Minute Live Demo Script (10 Minutes)

| Time | Speaker | What to Show on Screen | Exact Talking Points |
| :--- | :--- | :--- | :--- |
| **0:00 – 1:00** | **Yashvant (ATK)** | `docs/er_diagram.png` & Problem Overview | *"We built **CineBook**, a multiplex ticket booking system backed by PostgreSQL 16 and FastAPI using raw SQL with no ORM. In manual or file-based tracking, two customers can double-book the same seat, cancellations leave seats blocked, and managers lack live occupancy and revenue data. Our 12-table design in Third Normal Form (3NF) enforces one-seat-one-customer-per-show inside PostgreSQL itself using row-level locking (`FOR UPDATE`) and a partial unique index on active tickets."* |
| **1:00 – 3:00** | **Tharanesh** | `pgAdmin` / `psql` terminal showing the 12 tables & constraints | Show the 12 tables (`Customer`, `Movie`, `Genre`, `Movie_Genre`, `Theatre`, `Screen`, `Seat`, `Show`, `Show_Pricing`, `Booking`, `Ticket`, `Payment`). Run a bad insert (e.g., negative ticket price or rating `12.5` or overlapping show on Screen 1) to show PostgreSQL constraints and `trg_prevent_show_overlap` rejecting invalid data immediately. |
| **3:00 – 6:00** | **Mohit** | Browser 1 (`http://localhost:8000`) Customer Flow | Log in as `tharanesh@cinebook.in` (`password123`). Filter movies on `/movies` by language (`Tamil`) and rating (`>= 8.0`). Open **Leo** (`/movies/1`), show live `seats_left` per show, click **Select Seats** on an upcoming show, point out `REGULAR` (`A–C`), `PREMIUM` (`D–E`), and `RECLINER` (`F`) pricing tiers, select 2 seats, choose **UPI** or **Card** on `/checkout`, and confirm payment to show the generated ticket on `/confirmation/{id}`. |
| **6:00 – 7:00** | **Tharanesh** | Browser 1 & Browser 2 side-by-side (Concurrency & Cancellation) | Open the same show's seat map in both browsers. Select the **same seat (e.g., `B-5`)** in both and click Checkout. Submit payment in Browser 1 (succeeds!), then submit in Browser 2 (rejected with *"Seat(s) B-5 already booked"*). Next, in Browser 1 go to `/my-bookings`, click **Cancel Booking** (`> 2 hours` away): show status changing to `CANCELLED`, payment to `REFUNDED`, and refresh Browser 2 to show seat `B-5` is immediately available again. |
| **7:00 – 9:00** | **Yashvant (ATK)** | Admin Dashboard (`/admin`), `/reports/*`, & `db/queries.sql` in terminal | Log in as `admin@cinebook.in` (`password123`) and open `/admin`. Show the 5 aggregate KPI cards (`COUNT`, `SUM`, `AVG`, `MIN`, `MAX` — Query #3) and click through **Revenue by Movie** (Queries #4–5), **Occupancy with Above-Average Subquery filter** (`show_availability` view & Query #10), **Top Customers** (Query #11), **Daily Sales** (Query #12), **Unsold Movies** (*Kanguva* — Query #9), **Inactive Customers** (*Meera Krishnan* — Query #8), and **Busiest Screens** (Query #14). In the terminal, run `psql -P pager=off -U postgres -d cinebook -f db/queries.sql` to show the live SQL output and the `DELETE` foreign-key protection demo on *Leo*. |
| **9:00 – 10:00** | **All Three** | Q&A / Summary | Summarize key learnings (why database-enforced invariants beat application-only checks) and invite examiner questions. |

## 3. Viva Questions & Crisp Answers Every Member Must Know (Plan Page 20)

| Viva Question | Crisp Technical Answer |
| :--- | :--- |
| **1. How do you stop two people booking one seat?** | Inside one database transaction, we lock the selected `Seat` rows using `SELECT ... FOR UPDATE` and check for existing `ACTIVE` tickets. As the final database-level guarantee, `Ticket` has a partial unique index `CREATE UNIQUE INDEX idx_ticket_active_seat ON Ticket(show_id, seat_id) WHERE status = 'ACTIVE'`, so PostgreSQL physically refuses a second active ticket for the same show and seat. |
| **2. Why store `price` on `Ticket` and `total_amount` on `Booking` when `Show_Pricing` already has the price?** | Show prices can be updated later by the admin (e.g., weekend surge pricing), but a historical booking receipt and refund calculation must preserve the exact price charged at the time of purchase. This is a deliberate, justified historical snapshot exception to strict normalization. |
| **3. Why is `Movie_Genre` a separate table?** | Because `Movie` and `Genre` have a many-to-many (`M:N`) relationship. Storing genres in a junction table with composite primary key `(movie_id, genre_id)` eliminates comma-separated repeating groups and satisfies First Normal Form (1NF). |
| **4. What is a transaction and where did you use it?** | A transaction is an atomic unit of work (`ACID`) where either all SQL statements commit or all roll back on error. We used transactions in **Booking** (`INSERT Booking` + `INSERT Ticket`s + `INSERT Payment` + `UPDATE Booking` to `CONFIRMED` with `FOR UPDATE` seat locks) and **Cancellation** (`UPDATE Booking` to `CANCELLED` + `UPDATE Ticket`s to `CANCELLED` + `UPDATE Payment` to `REFUNDED`). |
| **5. Why did you use SQL views (`show_availability`, `booking_summary`, `revenue_report`)?** | Nothing derivable (like screen capacity, seats left, or occupancy %) is stored as a table column, avoiding update anomalies. Views give one reusable, single-source-of-truth SQL definition shared by both customer pages and admin reports. |
| **6. What happens if you delete a movie that has scheduled shows?** | `Show.movie_id` references `Movie(movie_id) ON DELETE RESTRICT`, so PostgreSQL blocks the deletion with a foreign-key violation error. Deleting a movie with zero scheduled shows (like *Kanguva*, Movie #10) succeeds cleanly. |
| **7. Why did you write raw SQL with `psycopg` 3 instead of using an ORM like SQLAlchemy?** | To keep every `JOIN`, aggregate, `GROUP BY / HAVING`, subquery, view, trigger, and row lock (`FOR UPDATE`) 100% explicit, transparent, and tunable for the DBMS course evaluation. |
| **8. Which normal form is the database in, and how do you know?** | **Third Normal Form (3NF):** (1) **1NF** — all columns are atomic and `Movie_Genre` removes repeating genre lists; (2) **2NF** — in composite-key tables (`Show_Pricing(show_id, seat_category)` and `Movie_Genre(movie_id, genre_id)`), non-key attributes depend on the whole key; (3) **3NF** — no transitive dependencies exist (`Theatre`, `Movie`, and `Customer` attributes live only in their own tables), with `Ticket.price` and `Booking.total_amount` documented as deliberate historical snapshots. |
