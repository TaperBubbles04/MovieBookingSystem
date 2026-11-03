"""
Report service - wraps the 3 views and 14 queries from db/views.sql and db/queries.sql
"""

from datetime import date, timedelta
from typing import Optional


def get_revenue_by_movie(cur, date_from: Optional[date] = None, date_to: Optional[date] = None):
    """GET /reports/revenue-by-movie"""
    query = """
        SELECT movie_id, movie_title, total_revenue, tickets_sold, avg_price
        FROM revenue_report
    """
    params = []
    conditions = []

    if date_from:
        conditions.append("show_date >= %s")
        params.append(date_from)
    if date_to:
        conditions.append("show_date <= %s")
        params.append(date_to)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY total_revenue DESC"

    cur.execute(query, params)
    return cur.fetchall()


def get_occupancy(cur, date_from: Optional[date] = None, date_to: Optional[date] = None, theatre_id: Optional[int] = None, above_avg_only: bool = False):
    """GET /reports/occupancy"""
    query = """
        SELECT show_id, movie, theatre, screen, show_date, start_time,
               total_seats, booked_seats, seats_left, occupancy_pct
        FROM show_availability
    """
    params = []
    conditions = []

    if date_from:
        conditions.append("show_date >= %s")
        params.append(date_from)
    if date_to:
        conditions.append("show_date <= %s")
        params.append(date_to)
    if theatre_id:
        conditions.append("theatre_id = %s")
        params.append(theatre_id)

    if above_avg_only:
        conditions.append("occupancy_pct > (SELECT AVG(occupancy_pct) FROM show_availability)")

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY occupancy_pct DESC, show_id"

    cur.execute(query, params)
    return cur.fetchall()


def get_top_customers(cur, limit: int = 10, date_from: Optional[date] = None, date_to: Optional[date] = None):
    """GET /reports/top-customers"""
    query = """
        SELECT c.customer_id, c.name, c.email,
               COUNT(b.booking_id) AS bookings_count,
               SUM(b.total_amount) AS total_spent
        FROM Customer c
        JOIN Booking b ON b.customer_id = c.customer_id
        WHERE b.status = 'CONFIRMED'
          AND c.role = 'CUSTOMER'
    """
    params = []

    if date_from:
        query += " AND b.booking_time >= %s"
        params.append(date_from)
    if date_to:
        query += " AND b.booking_time <= %s"
        params.append(date_to)

    query += " GROUP BY c.customer_id, c.name, c.email ORDER BY total_spent DESC, bookings_count DESC LIMIT %s"
    params.append(limit)

    cur.execute(query, params)
    return cur.fetchall()


def get_daily_sales(cur, days: int = 7):
    """GET /reports/daily-sales"""
    date_from = date.today() - timedelta(days=days)

    query = """
        SELECT (b.booking_time AT TIME ZONE 'Asia/Kolkata')::DATE AS sale_date,
               COUNT(b.booking_id) AS bookings,
               SUM(b.total_amount) AS revenue
        FROM Booking b
        WHERE b.status = 'CONFIRMED'
          AND (b.booking_time AT TIME ZONE 'Asia/Kolkata')::DATE >= %s
        GROUP BY (b.booking_time AT TIME ZONE 'Asia/Kolkata')::DATE
        ORDER BY sale_date ASC
    """
    cur.execute(query, (date_from,))
    return cur.fetchall()


def get_unsold_movies(cur):
    """GET /reports/unsold-movies"""
    query = """
        SELECT m.movie_id, m.title, m.language, m.certificate
        FROM Movie m
        WHERE m.movie_id NOT IN (
            SELECT DISTINCT sh.movie_id FROM Show sh
        )
        ORDER BY m.movie_id
    """
    cur.execute(query)
    return cur.fetchall()


def get_unbooked_customers(cur):
    """GET /reports/unbooked-customers"""
    query = """
        SELECT c.customer_id, c.name, c.email, c.phone, c.created_at
        FROM Customer c
        WHERE c.role = 'CUSTOMER'
          AND NOT EXISTS (
              SELECT 1 FROM Booking b WHERE b.customer_id = c.customer_id
          )
        ORDER BY c.customer_id
    """
    cur.execute(query)
    return cur.fetchall()


def get_busiest_screens(cur):
    """GET /reports/busiest-screens"""
    query = """
        SELECT th.theatre_id, th.name AS theatre_name, th.city,
               sc.screen_id, sc.screen_name, sc.screen_type,
               COUNT(DISTINCT sh.show_id) AS total_shows,
               COUNT(tk.ticket_id) AS tickets_sold,
               COALESCE(SUM(tk.price), 0) AS total_revenue
        FROM Theatre th
        JOIN Screen sc ON sc.theatre_id = th.theatre_id
        LEFT JOIN Show sh ON sh.screen_id = sc.screen_id
        LEFT JOIN Booking b ON b.show_id = sh.show_id AND b.status = 'CONFIRMED'
        LEFT JOIN Ticket tk ON tk.booking_id = b.booking_id AND tk.status = 'ACTIVE'
        GROUP BY th.theatre_id, th.name, th.city, sc.screen_id, sc.screen_name, sc.screen_type
        ORDER BY tickets_sold DESC, total_revenue DESC
    """
    cur.execute(query)
    return cur.fetchall()


def get_admin_dashboard_summary(cur):
    """GET /reports/summary - aggregate stats for admin dashboard"""
    query = """
        SELECT
            COUNT(tk.ticket_id) AS total_tickets_sold,
            COALESCE(SUM(tk.price), 0) AS total_revenue_rs,
            ROUND(COALESCE(AVG(tk.price), 0), 2) AS avg_ticket_price_rs,
            COALESCE(MAX(tk.price), 0) AS highest_ticket_price_rs,
            COALESCE(MIN(tk.price), 0) AS lowest_ticket_price_rs
        FROM Ticket tk
        JOIN Booking b ON b.booking_id = tk.booking_id
        WHERE tk.status = 'ACTIVE'
          AND b.status = 'CONFIRMED'
    """
    cur.execute(query)
    return cur.fetchone()