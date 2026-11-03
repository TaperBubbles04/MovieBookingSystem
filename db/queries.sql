-- ============================================================================
-- CineBook Multiplex Booking System — SQL Showcase & Demo Queries (db/queries.sql)
-- Owner: Yashvant A T K (ATK — Admin, Data & Documentation Lead)
-- Target: PostgreSQL 16
-- Contents:
--   Part A: All 14 Course-Graded SQL Queries (each mapped to an app feature)
--   Part B: Verification Queries over the 3 Views (show_availability,
--           booking_summary, revenue_report)
--   Part C: Data-Changing Operations (INSERT, UPDATE, DELETE + FK block demo)
--   Part D: Extra-Credit Features (Trigger to recalculate booking total,
--           Stored Function get_seats_left, Show Overlap Trigger, Index + EXPLAIN)
-- ============================================================================

-- ============================================================================
-- PART A: 14 COURSE-GRADED QUERIES
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Query #1: Shows for a chosen movie on a chosen date, earliest first
-- Concepts: SELECT, WHERE, ORDER BY (plus JOINs for theatre & screen context)
-- App Screen: Customer Show Picker (GET /shows?movie_id=1&date=2026-10-31)
-- ----------------------------------------------------------------------------
\echo '=== QUERY 1: Shows for Movie #1 (Leo) on 2026-10-31, earliest first ==='
SELECT
    sh.show_id,
    m.title AS movie_title,
    th.name AS theatre_name,
    th.city,
    sc.screen_name,
    sc.screen_type,
    sh.show_date,
    sh.start_time,
    sh.end_time
FROM Show sh
JOIN Movie m ON m.movie_id = sh.movie_id
JOIN Screen sc ON sc.screen_id = sh.screen_id
JOIN Theatre th ON th.theatre_id = sc.theatre_id
WHERE sh.movie_id = 1
  AND sh.show_date = '2026-10-31'
ORDER BY sh.start_time ASC;


-- ----------------------------------------------------------------------------
-- Query #2: Movies filtered by language, certificate, minimum rating, or title
-- Concepts: WHERE with AND / OR, ILIKE / LIKE for partial title search
-- App Screen: Customer Movie List Search & Filter (GET /movies)
-- ----------------------------------------------------------------------------
\echo '=== QUERY 2: Movies filtered by language (Tamil/English), certificate (UA/U), rating >= 8.0, and LIKE search ==='
SELECT
    m.movie_id,
    m.title,
    m.language,
    m.certificate,
    m.duration_min,
    m.rating,
    m.release_date
FROM Movie m
WHERE (m.language = 'Tamil' OR m.language = 'English')
  AND m.certificate IN ('U', 'UA')
  AND m.rating >= 8.0
  AND m.title LIKE '%%'
ORDER BY m.rating DESC, m.title ASC;


-- ----------------------------------------------------------------------------
-- Query #3: Total tickets sold, total revenue, average, highest, and lowest ticket price
-- Concepts: Aggregate functions — COUNT, SUM, AVG, MIN, MAX
-- App Screen: Admin Dashboard Summary Cards (GET /reports/summary)
-- ----------------------------------------------------------------------------
\echo '=== QUERY 3: Admin Dashboard Aggregate Summary (COUNT, SUM, AVG, MIN, MAX) ==='
SELECT
    COUNT(tk.ticket_id) AS total_tickets_sold,
    COALESCE(SUM(tk.price), 0) AS total_revenue_rs,
    ROUND(COALESCE(AVG(tk.price), 0), 2) AS avg_ticket_price_rs,
    COALESCE(MAX(tk.price), 0) AS highest_ticket_price_rs,
    COALESCE(MIN(tk.price), 0) AS lowest_ticket_price_rs
FROM Ticket tk
JOIN Booking b ON b.booking_id = tk.booking_id
WHERE tk.status = 'ACTIVE'
  AND b.status = 'CONFIRMED';


-- ----------------------------------------------------------------------------
-- Query #4: Revenue and tickets sold per movie
-- Concepts: JOIN, GROUP BY, SUM, COUNT, AVG
-- App Screen: Admin Revenue Report (GET /reports/revenue-by-movie)
-- ----------------------------------------------------------------------------
\echo '=== QUERY 4: Revenue and Tickets Sold per Movie ==='
SELECT
    m.movie_id,
    m.title,
    m.language,
    COUNT(tk.ticket_id) AS tickets_sold,
    COALESCE(SUM(tk.price), 0) AS total_revenue,
    COALESCE(ROUND(AVG(tk.price)), 0) AS avg_price
FROM Movie m
JOIN Show sh ON sh.movie_id = m.movie_id
LEFT JOIN Booking b
    ON b.show_id = sh.show_id
   AND b.status = 'CONFIRMED'
LEFT JOIN Ticket tk
    ON tk.booking_id = b.booking_id
   AND tk.status = 'ACTIVE'
GROUP BY m.movie_id, m.title, m.language
ORDER BY total_revenue DESC, tickets_sold DESC;


-- ----------------------------------------------------------------------------
-- Query #5: Only movies whose revenue crosses a threshold (₹2,000+)
-- Concepts: GROUP BY with HAVING
-- App Screen: Admin Top Movies Report (GET /reports/revenue-by-movie?min_revenue=2000)
-- ----------------------------------------------------------------------------
\echo '=== QUERY 5: Top Movies Whose Revenue Crosses Threshold (HAVING SUM >= 2000) ==='
SELECT
    m.movie_id,
    m.title,
    m.language,
    COUNT(tk.ticket_id) AS tickets_sold,
    SUM(tk.price) AS total_revenue
FROM Movie m
JOIN Show sh ON sh.movie_id = m.movie_id
JOIN Booking b ON b.show_id = sh.show_id AND b.status = 'CONFIRMED'
JOIN Ticket tk ON tk.booking_id = b.booking_id AND tk.status = 'ACTIVE'
GROUP BY m.movie_id, m.title, m.language
HAVING SUM(tk.price) >= 2000
ORDER BY total_revenue DESC;


-- ----------------------------------------------------------------------------
-- Query #6: Full booking details: customer, movie, theatre, screen, show time, seat labels
-- Concepts: Multi-table JOIN across 7 tables (Booking, Customer, Show, Movie,
--           Screen, Theatre, Ticket, Seat, Payment)
-- App Screen: Booking Confirmation & My Bookings History (GET /bookings/{id}, GET /bookings/me)
-- ----------------------------------------------------------------------------
\echo '=== QUERY 6: Full Booking Details (Multi-Table JOIN across 8 tables) ==='
SELECT
    b.booking_id,
    c.name AS customer_name,
    c.email AS customer_email,
    m.title AS movie_title,
    th.name AS theatre_name,
    th.city,
    sc.screen_name,
    sc.screen_type,
    sh.show_date,
    sh.start_time,
    STRING_AGG(st.row_label || '-' || st.seat_number, ', ' ORDER BY st.row_label, st.seat_number) AS seat_labels,
    b.total_amount,
    b.status AS booking_status,
    p.method AS payment_method,
    p.status AS payment_status
FROM Booking b
JOIN Customer c ON c.customer_id = b.customer_id
JOIN Show sh ON sh.show_id = b.show_id
JOIN Movie m ON m.movie_id = sh.movie_id
JOIN Screen sc ON sc.screen_id = sh.screen_id
JOIN Theatre th ON th.theatre_id = sc.theatre_id
JOIN Ticket tk ON tk.booking_id = b.booking_id
JOIN Seat st ON st.seat_id = tk.seat_id
LEFT JOIN Payment p ON p.booking_id = b.booking_id
GROUP BY
    b.booking_id, c.name, c.email, m.title, th.name, th.city,
    sc.screen_name, sc.screen_type, sh.show_date, sh.start_time,
    b.total_amount, b.status, p.method, p.status
ORDER BY b.booking_id ASC
LIMIT 10;


-- ----------------------------------------------------------------------------
-- Query #7: All movies, including those with no shows yet
-- Concepts: LEFT JOIN (preserves Movie #10 'Kanguva' with 0 scheduled shows)
-- App Screen: Admin Movie Management List (GET /movies)
-- ----------------------------------------------------------------------------
\echo '=== QUERY 7: All Movies Including Those With No Shows Yet (LEFT JOIN) ==='
SELECT
    m.movie_id,
    m.title,
    m.language,
    m.certificate,
    m.rating,
    COUNT(sh.show_id) AS scheduled_shows_count
FROM Movie m
LEFT JOIN Show sh ON sh.movie_id = m.movie_id
GROUP BY m.movie_id, m.title, m.language, m.certificate, m.rating
ORDER BY scheduled_shows_count ASC, m.movie_id ASC;


-- ----------------------------------------------------------------------------
-- Query #8: Customers who have never booked
-- Concepts: Correlated Subquery with NOT EXISTS (also equivalent to NOT IN)
-- App Screen: Admin Customer Report (GET /reports/unbooked-customers)
-- ----------------------------------------------------------------------------
\echo '=== QUERY 8: Customers Who Have Never Booked (Subquery with NOT EXISTS) ==='
SELECT
    c.customer_id,
    c.name,
    c.email,
    c.phone,
    c.created_at
FROM Customer c
WHERE c.role = 'CUSTOMER'
  AND NOT EXISTS (
      SELECT 1
      FROM Booking b
      WHERE b.customer_id = c.customer_id
  )
ORDER BY c.customer_id;


-- ----------------------------------------------------------------------------
-- Query #9: Movies that have no scheduled show
-- Concepts: Subquery with NOT IN
-- App Screen: Admin Unsold Movies Report (GET /reports/unsold-movies)
-- ----------------------------------------------------------------------------
\echo '=== QUERY 9: Movies With No Scheduled Shows (Subquery) ==='
SELECT
    m.movie_id,
    m.title,
    m.language,
    m.certificate,
    m.release_date
FROM Movie m
WHERE m.movie_id NOT IN (
    SELECT DISTINCT sh.movie_id
    FROM Show sh
)
ORDER BY m.movie_id;


-- ----------------------------------------------------------------------------
-- Query #10: Shows whose occupancy is above the average occupancy across all shows
-- Concepts: Subquery with aggregate (AVG over show occupancy)
-- App Screen: Admin Occupancy Report (GET /reports/occupancy?above_avg_only=true)
-- ----------------------------------------------------------------------------
\echo '=== QUERY 10: Shows Whose Occupancy Is Above the Average Occupancy ==='
SELECT
    sa.show_id,
    sa.movie,
    sa.theatre,
    sa.screen,
    sa.show_date,
    sa.start_time,
    sa.total_seats,
    sa.booked_seats,
    sa.seats_left,
    sa.occupancy_pct
FROM show_availability sa
WHERE sa.occupancy_pct > (
    SELECT AVG(sub.occupancy_pct)
    FROM show_availability sub
)
ORDER BY sa.occupancy_pct DESC, sa.show_id ASC;


-- ----------------------------------------------------------------------------
-- Query #11: Top customers by money spent
-- Concepts: GROUP BY, ORDER BY, LIMIT
-- App Screen: Admin Top Customers Report (GET /reports/top-customers)
-- ----------------------------------------------------------------------------
\echo '=== QUERY 11: Top Customers by Money Spent (GROUP BY, ORDER BY, LIMIT) ==='
SELECT
    c.customer_id,
    c.name,
    c.email,
    COUNT(b.booking_id) AS bookings_count,
    SUM(b.total_amount) AS total_spent
FROM Customer c
JOIN Booking b ON b.customer_id = c.customer_id
WHERE b.status = 'CONFIRMED'
GROUP BY c.customer_id, c.name, c.email
ORDER BY total_spent DESC, bookings_count DESC
LIMIT 10;


-- ----------------------------------------------------------------------------
-- Query #12: Daily sales for the last 7 days
-- Concepts: GROUP BY on a date column
-- App Screen: Admin Dashboard Daily Sales Chart (GET /reports/daily-sales)
-- ----------------------------------------------------------------------------
\echo '=== QUERY 12: Daily Sales for the Last 7 Days (GROUP BY on date) ==='
SELECT
    (b.booking_time AT TIME ZONE 'Asia/Kolkata')::DATE AS sale_date,
    COUNT(b.booking_id) AS bookings,
    SUM(b.total_amount) AS revenue
FROM Booking b
WHERE b.status = 'CONFIRMED'
  AND (b.booking_time AT TIME ZONE 'Asia/Kolkata')::DATE >= DATE '2026-10-25'
GROUP BY (b.booking_time AT TIME ZONE 'Asia/Kolkata')::DATE
ORDER BY sale_date ASC;


-- ----------------------------------------------------------------------------
-- Query #13: Seats still available for a chosen show (e.g., show_id = 1)
-- Concepts: Subquery excluding active tickets for that show
-- App Screen: Customer Seat Map (GET /shows/{id}/seats)
-- ----------------------------------------------------------------------------
\echo '=== QUERY 13: Seats Still Available for Show #1 (Subquery Excluding Active Tickets) ==='
SELECT
    st.seat_id,
    st.row_label,
    st.seat_number,
    st.seat_category,
    sp.price
FROM Show sh
JOIN Seat st ON st.screen_id = sh.screen_id
JOIN Show_Pricing sp
    ON sp.show_id = sh.show_id
   AND sp.seat_category = st.seat_category
WHERE sh.show_id = 1
  AND st.seat_id NOT IN (
      SELECT tk.seat_id
      FROM Ticket tk
      WHERE tk.show_id = 1
        AND tk.status = 'ACTIVE'
  )
ORDER BY st.row_label ASC, st.seat_number ASC
LIMIT 15;


-- ----------------------------------------------------------------------------
-- Query #14: Busiest theatre and screen by tickets sold
-- Concepts: Aggregate over multi-table JOINs
-- App Screen: Admin Occupancy Report — Busiest Screens (GET /reports/busiest-screens)
-- ----------------------------------------------------------------------------
\echo '=== QUERY 14: Busiest Theatre and Screen by Tickets Sold ==='
SELECT
    th.theatre_id,
    th.name AS theatre_name,
    th.city,
    sc.screen_id,
    sc.screen_name,
    sc.screen_type,
    COUNT(DISTINCT sh.show_id) AS total_shows,
    COUNT(tk.ticket_id) AS tickets_sold,
    COALESCE(SUM(tk.price), 0) AS total_revenue
FROM Theatre th
JOIN Screen sc ON sc.theatre_id = th.theatre_id
LEFT JOIN Show sh ON sh.screen_id = sc.screen_id
LEFT JOIN Booking b ON b.show_id = sh.show_id AND b.status = 'CONFIRMED'
LEFT JOIN Ticket tk ON tk.booking_id = b.booking_id AND tk.status = 'ACTIVE'
GROUP BY th.theatre_id, th.name, th.city, sc.screen_id, sc.screen_name, sc.screen_type
ORDER BY tickets_sold DESC, total_revenue DESC;


-- ============================================================================
-- PART B: SHOWCASE OF THE 3 VIEWS
-- ============================================================================

\echo '=== VIEW 1: show_availability (First 8 rows) ==='
SELECT show_id, movie, theatre, screen, show_date, start_time, total_seats, booked_seats, seats_left, occupancy_pct
FROM show_availability
ORDER BY show_id
LIMIT 8;

\echo '=== VIEW 2: booking_summary (First 8 rows) ==='
SELECT booking_id, customer_name, movie_title, theatre_name, show_date, start_time, seats, total_amount, booking_status, payment_status
FROM booking_summary
ORDER BY booking_id
LIMIT 8;

\echo '=== VIEW 3: revenue_report (First 8 rows) ==='
SELECT show_date, movie_title, theatre_name, shows_count, confirmed_bookings, tickets_sold, total_revenue, avg_price
FROM revenue_report
ORDER BY show_date DESC, total_revenue DESC
LIMIT 8;


-- ============================================================================
-- PART C: OPTIONAL EXTRAS FOR EXTRA CREDIT (Triggers, Stored Function, Index)
-- ============================================================================

-- 1. Extra Credit Trigger: Prevent overlapping shows on the same screen & date
CREATE OR REPLACE FUNCTION fn_prevent_show_overlap()
RETURNS TRIGGER AS $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM Show s
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

DROP TRIGGER IF EXISTS trg_prevent_show_overlap ON Show;
CREATE TRIGGER trg_prevent_show_overlap
BEFORE INSERT OR UPDATE ON Show
FOR EACH ROW
EXECUTE FUNCTION fn_prevent_show_overlap();


-- 2. Extra Credit Trigger: Recalculate Booking.total_amount when active Tickets change
CREATE OR REPLACE FUNCTION fn_recalc_booking_total()
RETURNS TRIGGER AS $$
DECLARE
    v_booking_id INT;
BEGIN
    v_booking_id := COALESCE(NEW.booking_id, OLD.booking_id);
    UPDATE Booking
    SET total_amount = COALESCE((
        SELECT SUM(price)
        FROM Ticket
        WHERE booking_id = v_booking_id
          AND status = 'ACTIVE'
    ), 0)
    WHERE booking_id = v_booking_id
      AND status <> 'CANCELLED';
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_recalc_booking_total ON Ticket;
CREATE TRIGGER trg_recalc_booking_total
AFTER INSERT OR UPDATE OR DELETE ON Ticket
FOR EACH ROW
EXECUTE FUNCTION fn_recalc_booking_total();


-- 3. Extra Credit Stored Function: Return seats left for a given show_id
CREATE OR REPLACE FUNCTION get_seats_left(p_show_id INT)
RETURNS INT AS $$
DECLARE
    v_seats_left INT;
BEGIN
    SELECT seats_left
    INTO v_seats_left
    FROM show_availability
    WHERE show_id = p_show_id;

    RETURN COALESCE(v_seats_left, 0);
END;
$$ LANGUAGE plpgsql;

\echo '=== EXTRA CREDIT: Stored Function get_seats_left(1) ==='
SELECT get_seats_left(1) AS show_1_seats_left;


-- 4. Extra Credit Index on Show(show_date, movie_id) + EXPLAIN comparison
CREATE INDEX IF NOT EXISTS idx_show_date_movie ON Show (show_date, movie_id);

\echo '=== EXTRA CREDIT: EXPLAIN ANALYZE on Show Picker Lookup ==='
EXPLAIN ANALYZE
SELECT show_id, screen_id, start_time, end_time
FROM Show
WHERE show_date = '2026-10-31' AND movie_id = 1;


-- ============================================================================
-- PART D: DATA-CHANGING OPERATIONS DEMO (INSERT, UPDATE, DELETE)
-- Wrapped in BEGIN ... ROLLBACK so running queries.sql demonstrates every DML
-- feature and constraint check without permanently mutating the clean seed data.
-- ============================================================================
\echo '=== PART D: DML Demonstrations (INSERT, UPDATE, DELETE + FK Protection) ==='
BEGIN;

-- 1. INSERT Demo: Add a new movie with no shows, then update it, then delete it
INSERT INTO Movie (title, description, duration_min, language, certificate, release_date, rating)
VALUES ('vettaiyan Demo Movie', 'Temporary movie inserted to demonstrate INSERT, UPDATE, and DELETE.', 163, 'Tamil', 'UA', '2026-11-10', 8.0)
RETURNING movie_id, title, rating;

-- 2. UPDATE Demo: Edit movie rating and update a show price tier
UPDATE Movie
SET rating = 8.4, title = 'Vettaiyan (Updated)'
WHERE title = 'vettaiyan Demo Movie'
RETURNING movie_id, title, rating;

UPDATE Show_Pricing
SET price = price + 20
WHERE show_id = 30 AND seat_category = 'REGULAR'
RETURNING show_id, seat_category, price AS updated_price;

-- 3. DELETE Demo (Success): Remove a movie that has NO scheduled shows
DELETE FROM Movie
WHERE title = 'Vettaiyan (Updated)'
RETURNING movie_id, title AS deleted_movie_without_shows;

-- 4. DELETE Demo (Blocked by Foreign Key): Attempt to delete Movie #1 ('Leo') which HAS shows
DO $$
BEGIN
    DELETE FROM Movie WHERE movie_id = 1;
EXCEPTION
    WHEN foreign_key_violation THEN
        RAISE NOTICE 'EXPECTED CONSTRAINT BLOCK: Deleting Movie #1 (Leo) was refused by foreign key on Show.movie_id!';
END;
$$;

ROLLBACK;
\echo '=== ALL 14 QUERIES, 3 VIEWS, EXTRA-CREDIT TRIGGERS/FUNCTIONS & DML DEMOS COMPLETED ==='