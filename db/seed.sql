-- ============================================================================
-- CineBook Multiplex Booking System — Database Seed Script (db/seed.sql)
-- Owner: Yashvant A T K (ATK — Admin, Data & Documentation Lead)
-- Target: PostgreSQL 16
-- Purpose: Rebuilds and populates all 12 tables from scratch in one step with
--          realistic Indian multiplex data (Chennai & Bengaluru).
-- ============================================================================

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ----------------------------------------------------------------------------
-- 0. Safety Schema Guard (Creates the 12 tables in 3NF if not already created)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Customer (
    customer_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    phone VARCHAR(15) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'CUSTOMER' CHECK (role IN ('CUSTOMER', 'ADMIN')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS Movie (
    movie_id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    duration_min INT NOT NULL CHECK (duration_min > 0),
    language VARCHAR(50) NOT NULL,
    certificate VARCHAR(5) NOT NULL CHECK (certificate IN ('U', 'UA', 'A')),
    release_date DATE NOT NULL,
    rating NUMERIC(3, 1) CHECK (rating >= 0 AND rating <= 10),
    poster_url TEXT
);

CREATE TABLE IF NOT EXISTS Genre (
    genre_id SERIAL PRIMARY KEY,
    genre_name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS Movie_Genre (
    movie_id INT NOT NULL REFERENCES Movie(movie_id) ON DELETE CASCADE,
    genre_id INT NOT NULL REFERENCES Genre(genre_id) ON DELETE CASCADE,
    PRIMARY KEY (movie_id, genre_id)
);

CREATE TABLE IF NOT EXISTS Theatre (
    theatre_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    city VARCHAR(50) NOT NULL,
    address TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Screen (
    screen_id SERIAL PRIMARY KEY,
    theatre_id INT NOT NULL REFERENCES Theatre(theatre_id) ON DELETE CASCADE,
    screen_name VARCHAR(50) NOT NULL,
    screen_type VARCHAR(10) NOT NULL CHECK (screen_type IN ('2D', '3D', 'IMAX')),
    UNIQUE (theatre_id, screen_name)
);

CREATE TABLE IF NOT EXISTS Seat (
    seat_id SERIAL PRIMARY KEY,
    screen_id INT NOT NULL REFERENCES Screen(screen_id) ON DELETE CASCADE,
    row_label VARCHAR(5) NOT NULL,
    seat_number INT NOT NULL CHECK (seat_number > 0),
    seat_category VARCHAR(20) NOT NULL CHECK (seat_category IN ('REGULAR', 'PREMIUM', 'RECLINER')),
    UNIQUE (screen_id, row_label, seat_number)
);

CREATE TABLE IF NOT EXISTS Show (
    show_id SERIAL PRIMARY KEY,
    movie_id INT NOT NULL REFERENCES Movie(movie_id) ON DELETE RESTRICT,
    screen_id INT NOT NULL REFERENCES Screen(screen_id) ON DELETE CASCADE,
    show_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    CHECK (end_time > start_time),
    UNIQUE (screen_id, show_date, start_time)
);

CREATE TABLE IF NOT EXISTS Show_Pricing (
    show_id INT NOT NULL REFERENCES Show(show_id) ON DELETE CASCADE,
    seat_category VARCHAR(20) NOT NULL CHECK (seat_category IN ('REGULAR', 'PREMIUM', 'RECLINER')),
    price INT NOT NULL CHECK (price >= 0),
    PRIMARY KEY (show_id, seat_category)
);

CREATE TABLE IF NOT EXISTS Booking (
    booking_id SERIAL PRIMARY KEY,
    customer_id INT NOT NULL REFERENCES Customer(customer_id) ON DELETE RESTRICT,
    show_id INT NOT NULL REFERENCES Show(show_id) ON DELETE RESTRICT,
    booking_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    total_amount INT NOT NULL CHECK (total_amount >= 0),
    status VARCHAR(20) NOT NULL CHECK (status IN ('PENDING', 'CONFIRMED', 'CANCELLED'))
);

CREATE TABLE IF NOT EXISTS Ticket (
    ticket_id SERIAL PRIMARY KEY,
    booking_id INT NOT NULL REFERENCES Booking(booking_id) ON DELETE CASCADE,
    show_id INT NOT NULL REFERENCES Show(show_id) ON DELETE RESTRICT,
    seat_id INT NOT NULL REFERENCES Seat(seat_id) ON DELETE RESTRICT,
    price INT NOT NULL CHECK (price >= 0),
    status VARCHAR(20) NOT NULL CHECK (status IN ('ACTIVE', 'CANCELLED'))
);

-- Partial unique index: makes double booking of the same seat in a show impossible
CREATE UNIQUE INDEX IF NOT EXISTS idx_ticket_active_seat
    ON Ticket (show_id, seat_id)
    WHERE status = 'ACTIVE';

CREATE TABLE IF NOT EXISTS Payment (
    payment_id SERIAL PRIMARY KEY,
    booking_id INT NOT NULL REFERENCES Booking(booking_id) ON DELETE CASCADE,
    amount INT NOT NULL CHECK (amount > 0),
    method VARCHAR(20) NOT NULL CHECK (method IN ('UPI', 'CARD', 'CASH')),
    status VARCHAR(20) NOT NULL CHECK (status IN ('SUCCESS', 'FAILED', 'REFUNDED')),
    paid_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ----------------------------------------------------------------------------
-- 1. Clean Reset (Idempotent rebuild from scratch)
-- ----------------------------------------------------------------------------
TRUNCATE TABLE
    Payment,
    Ticket,
    Booking,
    Show_Pricing,
    Show,
    Seat,
    Screen,
    Theatre,
    Movie_Genre,
    Genre,
    Movie,
    Customer
RESTART IDENTITY CASCADE;

-- ----------------------------------------------------------------------------
-- 2. Genre (8 rows)
-- ----------------------------------------------------------------------------
INSERT INTO Genre (genre_name) VALUES
    ('Action'),     -- 1
    ('Drama'),      -- 2
    ('Comedy'),     -- 3
    ('Thriller'),   -- 4
    ('Sci-Fi'),     -- 5
    ('Romance'),    -- 6
    ('Animation'),  -- 7
    ('Horror');     -- 8

-- ----------------------------------------------------------------------------
-- 3. Movie (10 rows: Tamil, Hindi, English, Telugu; Movie #10 has NO shows)
-- ----------------------------------------------------------------------------
INSERT INTO Movie (title, description, duration_min, language, certificate, release_date, rating, poster_url) VALUES
    -- 1
    ('Leo', 'A mild-mannered cafe owner in Kashmir becomes a local hero, drawing the attention of a ruthless drug cartel claiming he is their former cohort.', 164, 'Tamil', 'UA', '2026-10-16', 8.1, 'https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=600'),
    -- 2
    ('Vikram', 'A special investigator discovers a case of serial killings is not what it seems to be, leading to a high-stakes war between rival vigilanteand syndicate factions.', 174, 'Tamil', 'UA', '2026-09-25', 8.6, 'https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=600'),
    -- 3
    ('Jawan', 'A prison warden recruits inmates to commit high-profile heists that expose corruption and bring justice to everyday citizens.', 169, 'Hindi', 'UA', '2026-10-02', 7.8, 'https://images.unsplash.com/photo-1517604931442-7e0c8ed2963c?w=600'),
    -- 4
    ('Stree 2', 'The town of Chanderi faces a new supernatural terror in the form of Sarkata, forcing Vicky and his friends to reunite for a rescue mission.', 147, 'Hindi', 'UA', '2026-10-10', 8.2, 'https://images.unsplash.com/photo-1509198397868-475647b2a1e5?w=600'),
    -- 5
    ('Oppenheimer', 'The story of theoretical physicist J. Robert Oppenheimer and his role in designing the atomic bomb during World War II.', 180, 'English', 'A', '2026-08-15', 8.9, 'https://images.unsplash.com/photo-1440404653325-ab127d49abc1?w=600'),
    -- 6
    ('Dune: Part Two', 'Paul Atreides unites with Chani and the Fremen while on a warpath of revenge against the conspirators who destroyed his family.', 166, 'English', 'UA', '2026-09-12', 8.8, 'https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=600'),
    -- 7
    ('Kalki 2898 AD', 'In a post-apocalyptic desert city, a bounty hunter and an immortal warrior cross paths to protect a prophesied child.', 181, 'Telugu', 'UA', '2026-10-09', 8.0, 'https://images.unsplash.com/photo-1508739773434-c26b3d09e071?w=600'),
    -- 8
    ('Hi Nanna', 'A doting single father begins to narrate the story of his missing wife to his six-year-old daughter with cystic fibrosis.', 155, 'Telugu', 'U', '2026-09-20', 8.3, 'https://images.unsplash.com/photo-1516589178581-6cd7833ae3b2?w=600'),
    -- 9
    ('Spider-Man: Across the Spider-Verse', 'Miles Morales catapults across the Multiverse, where he encounters a team of Spider-People charged with protecting its very existence.', 140, 'English', 'U', '2026-08-28', 8.7, 'https://images.unsplash.com/photo-1635805737707-575885ab0820?w=600'),
    -- 10 (Intentionally has NO scheduled shows — powers Query #7 LEFT JOIN, Query #9 Unsold Movies subquery, and DELETE test)
    ('Kanguva', 'A tribal warrior fierce struggle to save his people a millennium ago is mysteriously linked to a shadow cop in the present.', 154, 'Tamil', 'UA', '2026-11-14', 7.5, 'https://images.unsplash.com/photo-1574375927938-d5a98e8ffe85?w=600');

-- ----------------------------------------------------------------------------
-- 4. Movie_Genre (22 mappings resolving M:N)
-- ----------------------------------------------------------------------------
INSERT INTO Movie_Genre (movie_id, genre_id) VALUES
    (1, 1), (1, 4),         -- Leo: Action, Thriller
    (2, 1), (2, 4),         -- Vikram: Action, Thriller
    (3, 1), (3, 2),         -- Jawan: Action, Drama
    (4, 3), (4, 8),         -- Stree 2: Comedy, Horror
    (5, 2), (5, 4),         -- Oppenheimer: Drama, Thriller
    (6, 5), (6, 1), (6, 2), -- Dune: Part Two: Sci-Fi, Action, Drama
    (7, 5), (7, 1),         -- Kalki 2898 AD: Sci-Fi, Action
    (8, 2), (8, 6),         -- Hi Nanna: Drama, Romance
    (9, 7), (9, 1), (9, 5), -- Spider-Verse: Animation, Action, Sci-Fi
    (10, 1), (10, 2);       -- Kanguva: Action, Drama

-- ----------------------------------------------------------------------------
-- 5. Theatre (2 rows: Chennai & Bengaluru)
-- ----------------------------------------------------------------------------
INSERT INTO Theatre (name, city, address) VALUES
    ('PVR Phoenix Marketcity', 'Chennai', '142, Velachery Main Rd, Indira Gandhi Nagar, Velachery, Chennai, Tamil Nadu 600042'),
    ('INOX Mantri Square', 'Bengaluru', 'No. 1, Sampige Rd, Malleshwaram, Bengaluru, Karnataka 560003');

-- ----------------------------------------------------------------------------
-- 6. Screen (5 rows: Mix of IMAX, 3D, and 2D across Chennai & Bengaluru)
-- ----------------------------------------------------------------------------
INSERT INTO Screen (theatre_id, screen_name, screen_type) VALUES
    (1, 'Screen 1', 'IMAX'), -- screen_id = 1 (Chennai, 60 seats: seat_id 1..60)
    (1, 'Screen 2', '3D'),   -- screen_id = 2 (Chennai, 50 seats: seat_id 61..110)
    (1, 'Screen 3', '2D'),   -- screen_id = 3 (Chennai, 40 seats: seat_id 111..150)
    (2, 'Screen 1', 'IMAX'), -- screen_id = 4 (Bengaluru, 60 seats: seat_id 151..210)
    (2, 'Screen 2', '2D');   -- screen_id = 5 (Bengaluru, 50 seats: seat_id 211..260)

-- ----------------------------------------------------------------------------
-- 7. Seat (260 rows total across 5 screens; 40 to 60 seats per screen)
--    Front rows = REGULAR, penultimate rows = PREMIUM, back row = RECLINER
-- ----------------------------------------------------------------------------

-- Screen 1 (Chennai IMAX): 60 seats (Rows A-F, 10 seats/row) -> seat_id 1..60
INSERT INTO Seat (screen_id, row_label, seat_number, seat_category)
SELECT
    1,
    r.row_label,
    s.seat_no,
    CASE
        WHEN r.row_label IN ('A', 'B', 'C') THEN 'REGULAR'
        WHEN r.row_label IN ('D', 'E') THEN 'PREMIUM'
        ELSE 'RECLINER'
    END
FROM (VALUES ('A', 1), ('B', 2), ('C', 3), ('D', 4), ('E', 5), ('F', 6)) AS r(row_label, ord)
CROSS JOIN generate_series(1, 10) AS s(seat_no)
ORDER BY r.ord, s.seat_no;

-- Screen 2 (Chennai 3D): 50 seats (Rows A-E, 10 seats/row) -> seat_id 61..110
INSERT INTO Seat (screen_id, row_label, seat_number, seat_category)
SELECT
    2,
    r.row_label,
    s.seat_no,
    CASE
        WHEN r.row_label IN ('A', 'B', 'C') THEN 'REGULAR'
        WHEN r.row_label = 'D' THEN 'PREMIUM'
        ELSE 'RECLINER'
    END
FROM (VALUES ('A', 1), ('B', 2), ('C', 3), ('D', 4), ('E', 5)) AS r(row_label, ord)
CROSS JOIN generate_series(1, 10) AS s(seat_no)
ORDER BY r.ord, s.seat_no;

-- Screen 3 (Chennai 2D): 40 seats (Rows A-E, 8 seats/row) -> seat_id 111..150
INSERT INTO Seat (screen_id, row_label, seat_number, seat_category)
SELECT
    3,
    r.row_label,
    s.seat_no,
    CASE
        WHEN r.row_label IN ('A', 'B', 'C') THEN 'REGULAR'
        WHEN r.row_label = 'D' THEN 'PREMIUM'
        ELSE 'RECLINER'
    END
FROM (VALUES ('A', 1), ('B', 2), ('C', 3), ('D', 4), ('E', 5)) AS r(row_label, ord)
CROSS JOIN generate_series(1, 8) AS s(seat_no)
ORDER BY r.ord, s.seat_no;

-- Screen 4 (Bengaluru IMAX): 60 seats (Rows A-F, 10 seats/row) -> seat_id 151..210
INSERT INTO Seat (screen_id, row_label, seat_number, seat_category)
SELECT
    4,
    r.row_label,
    s.seat_no,
    CASE
        WHEN r.row_label IN ('A', 'B', 'C') THEN 'REGULAR'
        WHEN r.row_label IN ('D', 'E') THEN 'PREMIUM'
        ELSE 'RECLINER'
    END
FROM (VALUES ('A', 1), ('B', 2), ('C', 3), ('D', 4), ('E', 5), ('F', 6)) AS r(row_label, ord)
CROSS JOIN generate_series(1, 10) AS s(seat_no)
ORDER BY r.ord, s.seat_no;

-- Screen 5 (Bengaluru 2D): 50 seats (Rows A-E, 10 seats/row) -> seat_id 211..260
INSERT INTO Seat (screen_id, row_label, seat_number, seat_category)
SELECT
    5,
    r.row_label,
    s.seat_no,
    CASE
        WHEN r.row_label IN ('A', 'B', 'C') THEN 'REGULAR'
        WHEN r.row_label = 'D' THEN 'PREMIUM'
        ELSE 'RECLINER'
    END
FROM (VALUES ('A', 1), ('B', 2), ('C', 3), ('D', 4), ('E', 5)) AS r(row_label, ord)
CROSS JOIN generate_series(1, 10) AS s(seat_no)
ORDER BY r.ord, s.seat_no;

-- ----------------------------------------------------------------------------
-- 8. Show (32 shows across 7 days: 2026-10-27 to 2026-11-02; zero overlaps)
--    Movies 1..9 are scheduled; Movie 10 ('Kanguva') has 0 shows.
-- ----------------------------------------------------------------------------
INSERT INTO Show (movie_id, screen_id, show_date, start_time, end_time) VALUES
    -- Day 1: Tuesday 2026-10-27 (Past — for 7-day sales & reports)
    (1, 1, '2026-10-27', '10:00', '13:00'), -- show_id = 1  (Leo, Chennai IMAX)
    (5, 1, '2026-10-27', '18:30', '21:45'), -- show_id = 2  (Oppenheimer, Chennai IMAX)
    (3, 2, '2026-10-27', '14:00', '17:00'), -- show_id = 3  (Jawan, Chennai 3D)
    (6, 4, '2026-10-27', '19:00', '22:00'), -- show_id = 4  (Dune 2, Bengaluru IMAX)

    -- Day 2: Wednesday 2026-10-28 (Past)
    (2, 1, '2026-10-28', '10:30', '13:30'), -- show_id = 5  (Vikram, Chennai IMAX)
    (7, 2, '2026-10-28', '18:00', '21:15'), -- show_id = 6  (Kalki 2898 AD, Chennai 3D)
    (8, 3, '2026-10-28', '15:00', '17:45'), -- show_id = 7  (Hi Nanna, Chennai 2D)
    (4, 5, '2026-10-28', '19:30', '22:15'), -- show_id = 8  (Stree 2, Bengaluru 2D)

    -- Day 3: Thursday 2026-10-29 (Past)
    (1, 1, '2026-10-29', '14:00', '17:00'), -- show_id = 9  (Leo, Chennai IMAX)
    (9, 2, '2026-10-29', '11:00', '13:30'), -- show_id = 10 (Spider-Verse, Chennai 3D)
    (5, 4, '2026-10-29', '18:30', '21:45'), -- show_id = 11 (Oppenheimer, Bengaluru IMAX)
    (3, 5, '2026-10-29', '15:30', '18:30'), -- show_id = 12 (Jawan, Bengaluru 2D)

    -- Day 4: Friday 2026-10-30 (Past/Recent)
    (1, 1, '2026-10-30', '10:00', '13:00'), -- show_id = 13 (Leo, Chennai IMAX)
    (6, 1, '2026-10-30', '18:30', '21:30'), -- show_id = 14 (Dune 2, Chennai IMAX)
    (2, 3, '2026-10-30', '14:30', '17:30'), -- show_id = 15 (Vikram, Chennai 2D)
    (7, 4, '2026-10-30', '19:00', '22:15'), -- show_id = 16 (Kalki 2898 AD, Bengaluru IMAX)
    (4, 5, '2026-10-30', '16:00', '18:45'), -- show_id = 17 (Stree 2, Bengaluru 2D)

    -- Day 5: Saturday 2026-10-31 (Weekend — Higher Pricing)
    (1, 1, '2026-10-31', '10:00', '13:00'), -- show_id = 18 (Leo, Chennai IMAX)
    (5, 1, '2026-10-31', '14:30', '17:45'), -- show_id = 19 (Oppenheimer, Chennai IMAX)
    (7, 2, '2026-10-31', '18:30', '21:45'), -- show_id = 20 (Kalki 2898 AD, Chennai 3D)
    (8, 3, '2026-10-31', '11:30', '14:15'), -- show_id = 21 (Hi Nanna, Chennai 2D)
    (6, 4, '2026-10-31', '18:00', '21:00'), -- show_id = 22 (Dune 2, Bengaluru IMAX)
    (9, 5, '2026-10-31', '15:00', '17:30'), -- show_id = 23 (Spider-Verse, Bengaluru 2D)

    -- Day 6: Sunday 2026-11-01 (Weekend — Higher Pricing & Live Demo Target)
    (1, 1, '2026-11-01', '10:00', '13:00'), -- show_id = 24 (Leo, Chennai IMAX)
    (6, 1, '2026-11-01', '19:30', '22:30'), -- show_id = 25 (Dune 2, Chennai IMAX)
    (9, 2, '2026-11-01', '14:00', '16:30'), -- show_id = 26 (Spider-Verse, Chennai 3D)
    (4, 3, '2026-11-01', '18:30', '21:15'), -- show_id = 27 (Stree 2, Chennai 2D)
    (7, 4, '2026-11-01', '15:00', '18:15'), -- show_id = 28 (Kalki 2898 AD, Bengaluru IMAX)
    (3, 5, '2026-11-01', '19:00', '22:00'), -- show_id = 29 (Jawan, Bengaluru 2D)

    -- Day 7: Monday 2026-11-02 (Upcoming Weekday)
    (2, 1, '2026-11-02', '18:00', '21:00'), -- show_id = 30 (Vikram, Chennai IMAX)
    (8, 3, '2026-11-02', '14:00', '16:45'), -- show_id = 31 (Hi Nanna, Chennai 2D)
    (5, 4, '2026-11-02', '19:00', '22:15'); -- show_id = 32 (Oppenheimer, Bengaluru IMAX)

-- ----------------------------------------------------------------------------
-- 9. Show_Pricing (3 tiers per show = 96 rows; weekend & IMAX/3D priced higher)
--    - Weekday 2D (Screens 3, 5):         REGULAR 150, PREMIUM 220, RECLINER 350
--    - Weekday 3D (Screen 2):             REGULAR 180, PREMIUM 260, RECLINER 400
--    - Weekday IMAX (Screens 1, 4):       REGULAR 220, PREMIUM 320, RECLINER 480
--    - Weekend (Oct 31, Nov 01) +₹30/+₹40/+₹50 surcharge per tier
-- ----------------------------------------------------------------------------
INSERT INTO Show_Pricing (show_id, seat_category, price)
SELECT
    sh.show_id,
    cat.seat_category,
    CASE
        WHEN sc.screen_type = 'IMAX' AND sh.show_date IN ('2026-10-31', '2026-11-01') THEN
            CASE cat.seat_category WHEN 'REGULAR' THEN 250 WHEN 'PREMIUM' THEN 360 ELSE 530 END
        WHEN sc.screen_type = 'IMAX' THEN
            CASE cat.seat_category WHEN 'REGULAR' THEN 220 WHEN 'PREMIUM' THEN 320 ELSE 480 END
        WHEN sc.screen_type = '3D' AND sh.show_date IN ('2026-10-31', '2026-11-01') THEN
            CASE cat.seat_category WHEN 'REGULAR' THEN 210 WHEN 'PREMIUM' THEN 300 ELSE 450 END
        WHEN sc.screen_type = '3D' THEN
            CASE cat.seat_category WHEN 'REGULAR' THEN 180 WHEN 'PREMIUM' THEN 260 ELSE 400 END
        WHEN sh.show_date IN ('2026-10-31', '2026-11-01') THEN
            CASE cat.seat_category WHEN 'REGULAR' THEN 180 WHEN 'PREMIUM' THEN 260 ELSE 400 END
        ELSE
            CASE cat.seat_category WHEN 'REGULAR' THEN 150 WHEN 'PREMIUM' THEN 220 ELSE 350 END
    END AS price
FROM Show sh
JOIN Screen sc ON sc.screen_id = sh.screen_id
CROSS JOIN (VALUES ('REGULAR'), ('PREMIUM'), ('RECLINER')) AS cat(seat_category)
ORDER BY sh.show_id, cat.seat_category;

-- ----------------------------------------------------------------------------
-- 10. Customer (14 rows: 1 Admin, 12 Active Customers, 1 Customer who NEVER books)
--     Note: password_hash below is a standard bcrypt hash for 'password123'
-- ----------------------------------------------------------------------------
INSERT INTO Customer (name, email, phone, password_hash, role, created_at) VALUES
    -- 1: Admin Account
    ('Yashvant ATK', 'admin@cinebook.in', '9025106578', crypt('password123', gen_salt('bf', 10)), 'ADMIN', '2026-10-20 09:00:00+05:30'),
    -- 2..13: Customers with bookings
    ('Tharanesh R', 'tharanesh@cinebook.in', '9840112233', crypt('password123', gen_salt('bf', 10)), 'CUSTOMER', '2026-10-21 10:15:00+05:30'),
    ('Mohit Sharma', 'mohit@cinebook.in', '9840223344', crypt('password123', gen_salt('bf', 10)), 'CUSTOMER', '2026-10-21 11:30:00+05:30'),
    ('Ananya Iyer', 'ananya.iyer@gmail.com', '9840334455', crypt('password123', gen_salt('bf', 10)), 'CUSTOMER', '2026-10-22 14:20:00+05:30'),
    ('Karthik Subramanian', 'karthik.s@gmail.com', '9840445566', crypt('password123', gen_salt('bf', 10)), 'CUSTOMER', '2026-10-22 16:45:00+05:30'),
    ('Priya Nair', 'priya.nair@gmail.com', '9840556677', crypt('password123', gen_salt('bf', 10)), 'CUSTOMER', '2026-10-23 12:10:00+05:30'),
    ('Rohan Deshmukh', 'rohan.d@gmail.com', '9840667788', crypt('password123', gen_salt('bf', 10)), 'CUSTOMER', '2026-10-23 18:05:00+05:30'),
    ('Divya Menon', 'divya.menon@gmail.com', '9840778899', crypt('password123', gen_salt('bf', 10)), 'CUSTOMER', '2026-10-24 09:40:00+05:30'),
    ('Arjun Reddy', 'arjun.reddy@gmail.com', '9840889900', crypt('password123', gen_salt('bf', 10)), 'CUSTOMER', '2026-10-24 15:30:00+05:30'),
    ('Sneha Rao', 'sneha.rao@gmail.com', '9840990011', crypt('password123', gen_salt('bf', 10)), 'CUSTOMER', '2026-10-25 11:00:00+05:30'),
    ('Vikramaditya V', 'vikram.v@gmail.com', '9841001122', crypt('password123', gen_salt('bf', 10)), 'CUSTOMER', '2026-10-25 17:25:00+05:30'),
    ('Neha Gupta', 'neha.gupta@gmail.com', '9841112233', crypt('password123', gen_salt('bf', 10)), 'CUSTOMER', '2026-10-26 13:50:00+05:30'),
    ('Siddharth Malhotra', 'sid.m@gmail.com', '9841223344', crypt('password123', gen_salt('bf', 10)), 'CUSTOMER', '2026-10-26 19:15:00+05:30'),
    -- 14: Customer who NEVER books (powers Query #8 NOT EXISTS / NOT IN subquery)
    ('Meera Krishnan', 'meera.krishnan@gmail.com', '9841334455', crypt('password123', gen_salt('bf', 10)), 'CUSTOMER', '2026-10-27 10:00:00+05:30'),
    -- 15: Tharanesh's test account from README/commit message (also never booked initially)
    ('Test Customer', 'test@example.com', '9841445566', crypt('password123', gen_salt('bf', 10)), 'CUSTOMER', '2026-10-27 11:00:00+05:30');

-- ----------------------------------------------------------------------------
-- 11. Booking (32 rows: 27 CONFIRMED, 5 CANCELLED across 7 days)
--     Every total_amount matches the exact sum of its Ticket prices.
-- ----------------------------------------------------------------------------
INSERT INTO Booking (customer_id, show_id, booking_time, total_amount, status) VALUES
    -- Oct 27 bookings
    (2,  1,  '2026-10-27 08:30:00+05:30', 660,  'CONFIRMED'), -- booking_id = 1  (3x REGULAR @ 220)
    (3,  1,  '2026-10-27 09:00:00+05:30', 960,  'CONFIRMED'), -- booking_id = 2  (3x PREMIUM @ 320)
    (4,  2,  '2026-10-27 14:15:00+05:30', 960,  'CONFIRMED'), -- booking_id = 3  (2x RECLINER @ 480)
    (5,  3,  '2026-10-27 11:20:00+05:30', 540,  'CONFIRMED'), -- booking_id = 4  (3x REGULAR @ 180)
    (6,  4,  '2026-10-27 16:00:00+05:30', 640,  'CONFIRMED'), -- booking_id = 5  (2x PREMIUM @ 320)
    -- Cancelled booking on show 1 (seats 4, 5) followed by re-booking in booking_id = 7!
    (7,  1,  '2026-10-27 09:10:00+05:30', 440,  'CANCELLED'), -- booking_id = 6  (2x REGULAR @ 220 - CANCELLED)
    (8,  1,  '2026-10-27 09:25:00+05:30', 440,  'CONFIRMED'), -- booking_id = 7  (Re-booked seats 4, 5 @ 220!)

    -- Oct 28 bookings
    (9,  5,  '2026-10-28 08:45:00+05:30', 960,  'CONFIRMED'), -- booking_id = 8  (3x PREMIUM @ 320)
    (10, 6,  '2026-10-28 13:10:00+05:30', 800,  'CONFIRMED'), -- booking_id = 9  (2x RECLINER @ 400)
    (11, 7,  '2026-10-28 12:00:00+05:30', 450,  'CONFIRMED'), -- booking_id = 10 (3x REGULAR @ 150)
    (12, 8,  '2026-10-28 15:30:00+05:30', 660,  'CONFIRMED'), -- booking_id = 11 (3x PREMIUM @ 220)
    (13, 6,  '2026-10-28 14:00:00+05:30', 360,  'CANCELLED'), -- booking_id = 12 (2x REGULAR @ 180 - CANCELLED)

    -- Oct 29 bookings
    (2,  9,  '2026-10-29 10:00:00+05:30', 1440, 'CONFIRMED'), -- booking_id = 13 (3x RECLINER @ 480)
    (4,  10, '2026-10-29 09:15:00+05:30', 780,  'CONFIRMED'), -- booking_id = 14 (3x PREMIUM @ 260)
    (5,  11, '2026-10-29 13:45:00+05:30', 1280, 'CONFIRMED'), -- booking_id = 15 (4x PREMIUM @ 320)
    (6,  12, '2026-10-29 11:30:00+05:30', 700,  'CONFIRMED'), -- booking_id = 16 (2x RECLINER @ 350)

    -- Oct 30 bookings
    (3,  13, '2026-10-30 08:20:00+05:30', 880,  'CONFIRMED'), -- booking_id = 17 (4x REGULAR @ 220)
    (7,  14, '2026-10-30 12:10:00+05:30', 960,  'CONFIRMED'), -- booking_id = 18 (3x PREMIUM @ 320)
    (8,  15, '2026-10-30 10:30:00+05:30', 300,  'CANCELLED'), -- booking_id = 19 (2x REGULAR @ 150 - CANCELLED)
    (9,  16, '2026-10-30 14:00:00+05:30', 1440, 'CONFIRMED'), -- booking_id = 20 (3x RECLINER @ 480)
    (10, 17, '2026-10-30 11:45:00+05:30', 600,  'CONFIRMED'), -- booking_id = 21 (4x REGULAR @ 150)

    -- Oct 31 (Weekend) bookings
    (2,  18, '2026-10-31 08:00:00+05:30', 1080, 'CONFIRMED'), -- booking_id = 22 (3x PREMIUM @ 360)
    (4,  19, '2026-10-31 09:30:00+05:30', 1060, 'CONFIRMED'), -- booking_id = 23 (2x RECLINER @ 530)
    (5,  20, '2026-10-31 11:15:00+05:30', 900,  'CONFIRMED'), -- booking_id = 24 (3x PREMIUM @ 300)
    (11, 21, '2026-10-31 09:00:00+05:30', 360,  'CANCELLED'), -- booking_id = 25 (2x REGULAR @ 180 - CANCELLED)
    (12, 22, '2026-10-31 12:30:00+05:30', 1000, 'CONFIRMED'), -- booking_id = 26 (4x REGULAR @ 250)
    (13, 23, '2026-10-31 10:45:00+05:30', 800,  'CONFIRMED'), -- booking_id = 27 (2x RECLINER @ 400)

    -- Nov 01 (Weekend) & Nov 02 bookings
    (3,  24, '2026-10-31 18:00:00+05:30', 750,  'CONFIRMED'), -- booking_id = 28 (3x REGULAR @ 250)
    (6,  25, '2026-10-31 19:00:00+05:30', 1060, 'CONFIRMED'), -- booking_id = 29 (2x RECLINER @ 530)
    (7,  26, '2026-10-31 20:00:00+05:30', 630,  'CONFIRMED'), -- booking_id = 30 (3x REGULAR @ 210)
    (8,  28, '2026-10-31 20:30:00+05:30', 720,  'CANCELLED'), -- booking_id = 31 (2x PREMIUM @ 360 - CANCELLED)
    (9,  30, '2026-10-31 21:00:00+05:30', 640,  'CONFIRMED'); -- booking_id = 32 (2x PREMIUM @ 320)

-- ----------------------------------------------------------------------------
-- 12. Ticket (84 rows across the 32 bookings)
--     Seat ID ranges by screen:
--       Screen 1 (seat_id 1..60):   1..30 REGULAR, 31..50 PREMIUM, 51..60 RECLINER
--       Screen 2 (seat_id 61..110): 61..90 REGULAR, 91..100 PREMIUM, 101..110 RECLINER
--       Screen 3 (seat_id 111..150):111..134 REGULAR, 135..142 PREMIUM, 143..150 RECLINER
--       Screen 4 (seat_id 151..210):151..180 REGULAR, 181..200 PREMIUM, 201..210 RECLINER
--       Screen 5 (seat_id 211..260):211..240 REGULAR, 241..250 PREMIUM, 251..260 RECLINER
-- ----------------------------------------------------------------------------
INSERT INTO Ticket (booking_id, show_id, seat_id, price, status) VALUES
    -- Booking 1 (show 1, Screen 1, 3x REGULAR @ 220)
    (1, 1, 1, 220, 'ACTIVE'),
    (1, 1, 2, 220, 'ACTIVE'),
    (1, 1, 3, 220, 'ACTIVE'),
    -- Booking 2 (show 1, Screen 1, 3x PREMIUM @ 320)
    (2, 1, 31, 320, 'ACTIVE'),
    (2, 1, 32, 320, 'ACTIVE'),
    (2, 1, 33, 320, 'ACTIVE'),
    -- Booking 3 (show 2, Screen 1, 2x RECLINER @ 480)
    (3, 2, 51, 480, 'ACTIVE'),
    (3, 2, 52, 480, 'ACTIVE'),
    -- Booking 4 (show 3, Screen 2, 3x REGULAR @ 180)
    (4, 3, 61, 180, 'ACTIVE'),
    (4, 3, 62, 180, 'ACTIVE'),
    (4, 3, 63, 180, 'ACTIVE'),
    -- Booking 5 (show 4, Screen 4, 2x PREMIUM @ 320)
    (5, 4, 181, 320, 'ACTIVE'),
    (5, 4, 182, 320, 'ACTIVE'),
    -- Booking 6 (show 1, Screen 1, 2x REGULAR @ 220 - CANCELLED)
    (6, 1, 4, 220, 'CANCELLED'),
    (6, 1, 5, 220, 'CANCELLED'),
    -- Booking 7 (show 1, Screen 1, re-books seats 4 & 5 after Booking 6 cancelled!)
    (7, 1, 4, 220, 'ACTIVE'),
    (7, 1, 5, 220, 'ACTIVE'),
    -- Booking 8 (show 5, Screen 1, 3x PREMIUM @ 320)
    (8, 5, 34, 320, 'ACTIVE'),
    (8, 5, 35, 320, 'ACTIVE'),
    (8, 5, 36, 320, 'ACTIVE'),
    -- Booking 9 (show 6, Screen 2, 2x RECLINER @ 400)
    (9, 6, 101, 400, 'ACTIVE'),
    (9, 6, 102, 400, 'ACTIVE'),
    -- Booking 10 (show 7, Screen 3, 3x REGULAR @ 150)
    (10, 7, 111, 150, 'ACTIVE'),
    (10, 7, 112, 150, 'ACTIVE'),
    (10, 7, 113, 150, 'ACTIVE'),
    -- Booking 11 (show 8, Screen 5, 3x PREMIUM @ 220)
    (11, 8, 241, 220, 'ACTIVE'),
    (11, 8, 242, 220, 'ACTIVE'),
    (11, 8, 243, 220, 'ACTIVE'),
    -- Booking 12 (show 6, Screen 2, 2x REGULAR @ 180 - CANCELLED)
    (12, 6, 64, 180, 'CANCELLED'),
    (12, 6, 65, 180, 'CANCELLED'),
    -- Booking 13 (show 9, Screen 1, 3x RECLINER @ 480)
    (13, 9, 53, 480, 'ACTIVE'),
    (13, 9, 54, 480, 'ACTIVE'),
    (13, 9, 55, 480, 'ACTIVE'),
    -- Booking 14 (show 10, Screen 2, 3x PREMIUM @ 260)
    (14, 10, 91, 260, 'ACTIVE'),
    (14, 10, 92, 260, 'ACTIVE'),
    (14, 10, 93, 260, 'ACTIVE'),
    -- Booking 15 (show 11, Screen 4, 4x PREMIUM @ 320)
    (15, 11, 183, 320, 'ACTIVE'),
    (15, 11, 184, 320, 'ACTIVE'),
    (15, 11, 185, 320, 'ACTIVE'),
    (15, 11, 186, 320, 'ACTIVE'),
    -- Booking 16 (show 12, Screen 5, 2x RECLINER @ 350)
    (16, 12, 251, 350, 'ACTIVE'),
    (16, 12, 252, 350, 'ACTIVE'),
    -- Booking 17 (show 13, Screen 1, 4x REGULAR @ 220)
    (17, 13, 6, 220, 'ACTIVE'),
    (17, 13, 7, 220, 'ACTIVE'),
    (17, 13, 8, 220, 'ACTIVE'),
    (17, 13, 9, 220, 'ACTIVE'),
    -- Booking 18 (show 14, Screen 1, 3x PREMIUM @ 320)
    (18, 14, 37, 320, 'ACTIVE'),
    (18, 14, 38, 320, 'ACTIVE'),
    (18, 14, 39, 320, 'ACTIVE'),
    -- Booking 19 (show 15, Screen 3, 2x REGULAR @ 150 - CANCELLED)
    (19, 15, 114, 150, 'CANCELLED'),
    (19, 15, 115, 150, 'CANCELLED'),
    -- Booking 20 (show 16, Screen 4, 3x RECLINER @ 480)
    (20, 16, 201, 480, 'ACTIVE'),
    (20, 16, 202, 480, 'ACTIVE'),
    (20, 16, 203, 480, 'ACTIVE'),
    -- Booking 21 (show 17, Screen 5, 4x REGULAR @ 150)
    (21, 17, 211, 150, 'ACTIVE'),
    (21, 17, 212, 150, 'ACTIVE'),
    (21, 17, 213, 150, 'ACTIVE'),
    (21, 17, 214, 150, 'ACTIVE'),
    -- Booking 22 (show 18, Screen 1, Weekend, 3x PREMIUM @ 360)
    (22, 18, 40, 360, 'ACTIVE'),
    (22, 18, 41, 360, 'ACTIVE'),
    (22, 18, 42, 360, 'ACTIVE'),
    -- Booking 23 (show 19, Screen 1, Weekend, 2x RECLINER @ 530)
    (23, 19, 56, 530, 'ACTIVE'),
    (23, 19, 57, 530, 'ACTIVE'),
    -- Booking 24 (show 20, Screen 2, Weekend, 3x PREMIUM @ 300)
    (24, 20, 94, 300, 'ACTIVE'),
    (24, 20, 95, 300, 'ACTIVE'),
    (24, 20, 96, 300, 'ACTIVE'),
    -- Booking 25 (show 21, Screen 3, Weekend, 2x REGULAR @ 180 - CANCELLED)
    (25, 21, 116, 180, 'CANCELLED'),
    (25, 21, 117, 180, 'CANCELLED'),
    -- Booking 26 (show 22, Screen 4, Weekend, 4x REGULAR @ 250)
    (26, 22, 151, 250, 'ACTIVE'),
    (26, 22, 152, 250, 'ACTIVE'),
    (26, 22, 153, 250, 'ACTIVE'),
    (26, 22, 154, 250, 'ACTIVE'),
    -- Booking 27 (show 23, Screen 5, Weekend, 2x RECLINER @ 400)
    (27, 23, 253, 400, 'ACTIVE'),
    (27, 23, 254, 400, 'ACTIVE'),
    -- Booking 28 (show 24, Screen 1, Weekend, 3x REGULAR @ 250)
    (28, 24, 10, 250, 'ACTIVE'),
    (28, 24, 11, 250, 'ACTIVE'),
    (28, 24, 12, 250, 'ACTIVE'),
    -- Booking 29 (show 25, Screen 1, Weekend, 2x RECLINER @ 530)
    (29, 25, 58, 530, 'ACTIVE'),
    (29, 25, 59, 530, 'ACTIVE'),
    -- Booking 30 (show 26, Screen 2, Weekend, 3x REGULAR @ 210)
    (30, 26, 66, 210, 'ACTIVE'),
    (30, 26, 67, 210, 'ACTIVE'),
    (30, 26, 68, 210, 'ACTIVE'),
    -- Booking 31 (show 28, Screen 4, Weekend, 2x PREMIUM @ 360 - CANCELLED)
    (31, 28, 187, 360, 'CANCELLED'),
    (31, 28, 188, 360, 'CANCELLED'),
    -- Booking 32 (show 30, Screen 1, Weekday, 2x PREMIUM @ 320)
    (32, 30, 43, 320, 'ACTIVE'),
    (32, 30, 44, 320, 'ACTIVE');

-- ----------------------------------------------------------------------------
-- 13. Payment (32 rows: mix of UPI, CARD, CASH; SUCCESS, REFUNDED, FAILED)
-- ----------------------------------------------------------------------------
INSERT INTO Payment (booking_id, amount, method, status, paid_at) VALUES
    (1,  660,  'UPI',  'SUCCESS',  '2026-10-27 08:31:00+05:30'),
    (2,  960,  'CARD', 'SUCCESS',  '2026-10-27 09:01:00+05:30'),
    (3,  960,  'UPI',  'SUCCESS',  '2026-10-27 14:16:00+05:30'),
    (4,  540,  'CASH', 'SUCCESS',  '2026-10-27 11:21:00+05:30'),
    (5,  640,  'UPI',  'SUCCESS',  '2026-10-27 16:01:00+05:30'),
    (6,  440,  'UPI',  'REFUNDED', '2026-10-27 09:11:00+05:30'),
    (7,  440,  'CARD', 'SUCCESS',  '2026-10-27 09:26:00+05:30'),
    (8,  960,  'UPI',  'SUCCESS',  '2026-10-28 08:46:00+05:30'),
    (9,  800,  'CARD', 'SUCCESS',  '2026-10-28 13:11:00+05:30'),
    (10, 450,  'CASH', 'SUCCESS',  '2026-10-28 12:01:00+05:30'),
    (11, 660,  'UPI',  'SUCCESS',  '2026-10-28 15:31:00+05:30'),
    (12, 360,  'CARD', 'REFUNDED', '2026-10-28 14:01:00+05:30'),
    (13, 1440, 'CARD', 'SUCCESS',  '2026-10-29 10:01:00+05:30'),
    (14, 780,  'UPI',  'SUCCESS',  '2026-10-29 09:16:00+05:30'),
    (15, 1280, 'UPI',  'SUCCESS',  '2026-10-29 13:46:00+05:30'),
    (16, 700,  'CASH', 'SUCCESS',  '2026-10-29 11:31:00+05:30'),
    (17, 880,  'UPI',  'SUCCESS',  '2026-10-30 08:21:00+05:30'),
    (18, 960,  'CARD', 'SUCCESS',  '2026-10-30 12:11:00+05:30'),
    (19, 300,  'UPI',  'FAILED',   '2026-10-30 10:31:00+05:30'),
    (20, 1440, 'CARD', 'SUCCESS',  '2026-10-30 14:01:00+05:30'),
    (21, 600,  'CASH', 'SUCCESS',  '2026-10-30 11:46:00+05:30'),
    (22, 1080, 'UPI',  'SUCCESS',  '2026-10-31 08:01:00+05:30'),
    (23, 1060, 'CARD', 'SUCCESS',  '2026-10-31 09:31:00+05:30'),
    (24, 900,  'UPI',  'SUCCESS',  '2026-10-31 11:16:00+05:30'),
    (25, 360,  'UPI',  'REFUNDED', '2026-10-31 09:01:00+05:30'),
    (26, 1000, 'CARD', 'SUCCESS',  '2026-10-31 12:31:00+05:30'),
    (27, 800,  'UPI',  'SUCCESS',  '2026-10-31 10:46:00+05:30'),
    (28, 750,  'UPI',  'SUCCESS',  '2026-10-31 18:01:00+05:30'),
    (29, 1060, 'CARD', 'SUCCESS',  '2026-10-31 19:01:00+05:30'),
    (30, 630,  'CASH', 'SUCCESS',  '2026-10-31 20:01:00+05:30'),
    (31, 720,  'CARD', 'REFUNDED', '2026-10-31 20:31:00+05:30'),
    (32, 640,  'UPI',  'SUCCESS',  '2026-10-31 21:01:00+05:30');

COMMIT;