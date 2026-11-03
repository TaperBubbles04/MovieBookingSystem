-- ============================================================================
-- CineBook Multiplex Booking System — Database Views (db/views.sql)
-- Owner: Yashvant A T K (ATK — Admin, Data & Documentation Lead)
-- Target: PostgreSQL 16
-- Purpose: Defines the 3 core reusable views required by the course brief,
--          customer/admin pages, and `/reports/*` endpoints:
--            1. show_availability
--            2. booking_summary
--            3. revenue_report
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- View 1: show_availability
-- Contents: Per show: total seats, booked seats, seats left, occupancy %
-- Used by:  Show picker, GET /reports/occupancy, Occupancy report
-- Note:     Exposes both `movie`/`theatre`/`screen` (matching OccupancyItem in
--           backend/schemas/reports.py) and `movie_id`/`theatre_id`/`screen_id`
--           for filtering.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW show_availability AS
WITH screen_capacity AS (
    SELECT
        screen_id,
        COUNT(*) AS total_seats
    FROM Seat
    GROUP BY screen_id
),
active_tickets AS (
    SELECT
        show_id,
        COUNT(*) AS booked_seats
    FROM Ticket
    WHERE status = 'ACTIVE'
    GROUP BY show_id
)
SELECT
    sh.show_id,
    m.movie_id,
    m.title AS movie,
    th.theatre_id,
    th.name AS theatre,
    th.city,
    sc.screen_id,
    sc.screen_name AS screen,
    sc.screen_type,
    sh.show_date,
    sh.start_time,
    sh.end_time,
    COALESCE(cap.total_seats, 0)::INT AS total_seats,
    COALESCE(at.booked_seats, 0)::INT AS booked_seats,
    (COALESCE(cap.total_seats, 0) - COALESCE(at.booked_seats, 0))::INT AS seats_left,
    CASE
        WHEN COALESCE(cap.total_seats, 0) = 0 THEN 0.0
        ELSE ROUND((COALESCE(at.booked_seats, 0)::NUMERIC * 100.0) / cap.total_seats, 1)
    END AS occupancy_pct
FROM Show sh
JOIN Movie m ON m.movie_id = sh.movie_id
JOIN Screen sc ON sc.screen_id = sh.screen_id
JOIN Theatre th ON th.theatre_id = sc.theatre_id
LEFT JOIN screen_capacity cap ON cap.screen_id = sh.screen_id
LEFT JOIN active_tickets at ON at.show_id = sh.show_id;


-- ----------------------------------------------------------------------------
-- View 2: booking_summary
-- Contents: One row per booking with customer, movie, theatre, time, amount,
--           status, seat labels array, and payment status
-- Used by:  GET /bookings/me (My bookings), Admin bookings view
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW booking_summary AS
SELECT
    b.booking_id,
    c.customer_id,
    c.name AS customer_name,
    c.email AS customer_email,
    c.phone AS customer_phone,
    sh.show_id,
    m.movie_id,
    m.title AS movie_title,
    m.poster_url,
    th.theatre_id,
    th.name AS theatre_name,
    th.city,
    sc.screen_id,
    sc.screen_name,
    sc.screen_type,
    sh.show_date,
    sh.start_time,
    sh.end_time,
    b.booking_time,
    b.total_amount,
    b.status AS booking_status,
    COUNT(tk.ticket_id)::INT AS ticket_count,
    COALESCE(
        ARRAY_AGG(st.row_label || '-' || st.seat_number ORDER BY st.row_label, st.seat_number)
        FILTER (WHERE st.seat_id IS NOT NULL),
        ARRAY[]::TEXT[]
    ) AS seats,
    p.payment_id,
    p.method AS payment_method,
    p.status AS payment_status,
    p.paid_at
FROM Booking b
JOIN Customer c ON c.customer_id = b.customer_id
JOIN Show sh ON sh.show_id = b.show_id
JOIN Movie m ON m.movie_id = sh.movie_id
JOIN Screen sc ON sc.screen_id = sh.screen_id
JOIN Theatre th ON th.theatre_id = sc.theatre_id
LEFT JOIN Ticket tk ON tk.booking_id = b.booking_id
LEFT JOIN Seat st ON st.seat_id = tk.seat_id
LEFT JOIN Payment p ON p.booking_id = b.booking_id
GROUP BY
    b.booking_id,
    c.customer_id,
    c.name,
    c.email,
    c.phone,
    sh.show_id,
    m.movie_id,
    m.title,
    m.poster_url,
    th.theatre_id,
    th.name,
    th.city,
    sc.screen_id,
    sc.screen_name,
    sc.screen_type,
    sh.show_date,
    sh.start_time,
    sh.end_time,
    b.booking_time,
    b.total_amount,
    b.status,
    p.payment_id,
    p.method,
    p.status,
    p.paid_at;


-- ----------------------------------------------------------------------------
-- View 3: revenue_report
-- Contents: Revenue per movie, per theatre, and per day (from active tickets
--           on confirmed bookings)
-- Used by:  Admin dashboard (GET /reports/revenue-by-movie, /reports/daily-sales)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW revenue_report AS
SELECT
    sh.show_date,
    m.movie_id,
    m.title AS movie_title,
    m.language,
    m.certificate,
    th.theatre_id,
    th.name AS theatre_name,
    th.city,
    COUNT(DISTINCT sh.show_id)::INT AS shows_count,
    COUNT(DISTINCT b.booking_id)::INT AS confirmed_bookings,
    COUNT(tk.ticket_id)::INT AS tickets_sold,
    COALESCE(SUM(tk.price), 0)::INT AS total_revenue,
    COALESCE(ROUND(AVG(tk.price)), 0)::INT AS avg_price
FROM Show sh
JOIN Movie m ON m.movie_id = sh.movie_id
JOIN Screen sc ON sc.screen_id = sh.screen_id
JOIN Theatre th ON th.theatre_id = sc.theatre_id
LEFT JOIN Booking b
    ON b.show_id = sh.show_id
   AND b.status = 'CONFIRMED'
LEFT JOIN Ticket tk
    ON tk.booking_id = b.booking_id
   AND tk.status = 'ACTIVE'
GROUP BY
    sh.show_date,
    m.movie_id,
    m.title,
    m.language,
    m.certificate,
    th.theatre_id,
    th.name,
    th.city;

COMMIT;