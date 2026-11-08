-- ============================================================================
-- CineBook Multiplex Booking System — Database Schema (db/schema.sql)
-- Course: 25CS2004 Database Systems Design
-- Team: Tharanesh (Backend/DB), Mohit (Customer UI), Yashvant A T K (Admin/Data/Docs)
-- Database Engine: PostgreSQL 16 (12 Tables in Third Normal Form — 3NF)
-- ============================================================================

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 1. Customer (Roles live in Customer: CUSTOMER vs ADMIN)
CREATE TABLE IF NOT EXISTS Customer (
    customer_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    phone VARCHAR(15) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'CUSTOMER' CHECK (role IN ('CUSTOMER', 'ADMIN')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Movie
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

-- 3. Genre
CREATE TABLE IF NOT EXISTS Genre (
    genre_id SERIAL PRIMARY KEY,
    genre_name VARCHAR(50) NOT NULL UNIQUE
);

-- 4. Movie_Genre (Junction table resolving M:N between Movie and Genre)
CREATE TABLE IF NOT EXISTS Movie_Genre (
    movie_id INT NOT NULL REFERENCES Movie(movie_id) ON DELETE CASCADE,
    genre_id INT NOT NULL REFERENCES Genre(genre_id) ON DELETE CASCADE,
    PRIMARY KEY (movie_id, genre_id)
);

-- 5. Theatre
CREATE TABLE IF NOT EXISTS Theatre (
    theatre_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    city VARCHAR(50) NOT NULL,
    address TEXT NOT NULL
);

-- 6. Screen
CREATE TABLE IF NOT EXISTS Screen (
    screen_id SERIAL PRIMARY KEY,
    theatre_id INT NOT NULL REFERENCES Theatre(theatre_id) ON DELETE CASCADE,
    screen_name VARCHAR(50) NOT NULL,
    screen_type VARCHAR(10) NOT NULL CHECK (screen_type IN ('2D', '3D', 'IMAX')),
    UNIQUE (theatre_id, screen_name)
);

-- 7. Seat
CREATE TABLE IF NOT EXISTS Seat (
    seat_id SERIAL PRIMARY KEY,
    screen_id INT NOT NULL REFERENCES Screen(screen_id) ON DELETE CASCADE,
    row_label VARCHAR(5) NOT NULL,
    seat_number INT NOT NULL CHECK (seat_number > 0),
    seat_category VARCHAR(20) NOT NULL CHECK (seat_category IN ('REGULAR', 'PREMIUM', 'RECLINER')),
    UNIQUE (screen_id, row_label, seat_number)
);

-- 8. Show (ON DELETE RESTRICT on movie_id blocks deleting a movie that has shows)
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

-- 9. Show_Pricing (Composite PK; prices depend on whole key show_id + seat_category)
CREATE TABLE IF NOT EXISTS Show_Pricing (
    show_id INT NOT NULL REFERENCES Show(show_id) ON DELETE CASCADE,
    seat_category VARCHAR(20) NOT NULL CHECK (seat_category IN ('REGULAR', 'PREMIUM', 'RECLINER')),
    price INT NOT NULL CHECK (price >= 0),
    PRIMARY KEY (show_id, seat_category)
);

-- 10. Booking (total_amount is a justified historical snapshot)
CREATE TABLE IF NOT EXISTS Booking (
    booking_id SERIAL PRIMARY KEY,
    customer_id INT NOT NULL REFERENCES Customer(customer_id) ON DELETE RESTRICT,
    show_id INT NOT NULL REFERENCES Show(show_id) ON DELETE RESTRICT,
    booking_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    total_amount INT NOT NULL CHECK (total_amount >= 0),
    status VARCHAR(20) NOT NULL CHECK (status IN ('PENDING', 'CONFIRMED', 'CANCELLED'))
);

-- 11. Ticket (price is a justified historical snapshot; partial unique index blocks double booking)
CREATE TABLE IF NOT EXISTS Ticket (
    ticket_id SERIAL PRIMARY KEY,
    booking_id INT NOT NULL REFERENCES Booking(booking_id) ON DELETE CASCADE,
    show_id INT NOT NULL REFERENCES Show(show_id) ON DELETE RESTRICT,
    seat_id INT NOT NULL REFERENCES Seat(seat_id) ON DELETE RESTRICT,
    price INT NOT NULL CHECK (price >= 0),
    status VARCHAR(20) NOT NULL CHECK (status IN ('ACTIVE', 'CANCELLED'))
);

-- Partial Unique Index: guarantees at the database level that two active tickets
-- can never exist for the same show_id and seat_id, while cancelled tickets stay for history.
CREATE UNIQUE INDEX IF NOT EXISTS idx_ticket_active_seat
    ON Ticket (show_id, seat_id)
    WHERE status = 'ACTIVE';

-- Composite index for fast show picker lookup
CREATE INDEX IF NOT EXISTS idx_show_date_movie
    ON Show (show_date, movie_id);

-- 12. Payment
CREATE TABLE IF NOT EXISTS Payment (
    payment_id SERIAL PRIMARY KEY,
    booking_id INT NOT NULL REFERENCES Booking(booking_id) ON DELETE CASCADE,
    amount INT NOT NULL CHECK (amount > 0),
    method VARCHAR(20) NOT NULL CHECK (method IN ('UPI', 'CARD', 'CASH')),
    status VARCHAR(20) NOT NULL CHECK (status IN ('SUCCESS', 'FAILED', 'REFUNDED')),
    paid_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Trigger: Reject overlapping shows on the same screen and date
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

COMMIT;