from datetime import datetime

def create_booking(cur, customer_id: int, show_id: int, seat_ids: list, payment_method: str):
    """
    Atomic booking transaction:
    1. Validate show exists and not started
    2. Validate seats belong to show's screen
    3. Lock seats (FOR UPDATE)
    4. Check no active tickets for these seats
    5. Calculate total from Show_Pricing
    6. Insert booking (PENDING)
    7. Insert tickets (ACTIVE) with price snapshots
    8. Insert payment (SUCCESS)
    9. Update booking to CONFIRMED
    10. Commit
    """
    
    # 1. Validate show exists and get screen_id
    cur.execute("""
        SELECT s.show_id, s.screen_id, s.show_date, s.start_time
        FROM "show" s WHERE s.show_id = %s
    """, (show_id,))
    show = cur.fetchone()
    if not show:
        raise ValueError("Show not found")
    
    show_id, screen_id, show_date, start_time = show
    
    # Check show not started
    show_datetime = datetime.combine(show_date, start_time)
    if show_datetime <= datetime.now():
        raise ValueError("Show has already started")
    
    # 2. Validate all seats belong to this screen
    placeholders = ','.join(['%s'] * len(seat_ids))
    cur.execute(f"""
        SELECT seat_id FROM Seat WHERE seat_id IN ({placeholders}) AND screen_id = %s
    """, seat_ids + [screen_id])
    valid_seats = cur.fetchall()
    if len(valid_seats) != len(seat_ids):
        raise ValueError("One or more seats do not belong to this screen")
    
    # 3. Lock seats and check availability in one query
    cur.execute(f"""
        SELECT s.seat_id, st.row_label, st.seat_number, st.seat_category
        FROM Seat s
        JOIN Seat st ON s.seat_id = st.seat_id
        WHERE s.seat_id IN ({placeholders})
        FOR UPDATE
    """, seat_ids)
    locked_seats = cur.fetchall()
    
    # 4. Check no active tickets
    cur.execute(f"""
        SELECT seat_id FROM Ticket 
        WHERE show_id = %s AND seat_id IN ({placeholders}) AND status = 'ACTIVE'
        FOR SHARE
    """, [show_id] + seat_ids)
    taken = cur.fetchall()
    if taken:
        taken_seat_ids = [t[0] for t in taken]
        raise ValueError(f"Seat(s) {taken_seat_ids} already booked")
    
    # 5. Calculate total from Show_Pricing
    cur.execute("""
        SELECT seat_category, price FROM Show_Pricing WHERE show_id = %s
    """, (show_id,))
    pricing = {row[0]: row[1] for row in cur.fetchall()}
    
    total = 0
    seat_details = []
    for seat in locked_seats:
        seat_id, row_label, seat_number, seat_category = seat
        price = pricing.get(seat_category, 0)
        total += price
        seat_details.append({
            "seat_id": seat_id,
            "row_label": row_label,
            "seat_number": seat_number,
            "seat_category": seat_category,
            "price": price
        })
    
    # 6. Insert booking as PENDING
    cur.execute("""
        INSERT INTO Booking (customer_id, show_id, booking_time, total_amount, status)
        VALUES (%s, %s, NOW(), %s, 'PENDING')
        RETURNING booking_id
    """, (customer_id, show_id, total))
    booking_id = cur.fetchone()[0]
    
    # 7. Insert tickets with price snapshots
    for sd in seat_details:
        cur.execute("""
            INSERT INTO Ticket (booking_id, show_id, seat_id, price, status)
            VALUES (%s, %s, %s, %s, 'ACTIVE')
        """, (booking_id, show_id, sd["seat_id"], sd["price"]))
    
    # 8. Insert payment
    cur.execute("""
        INSERT INTO Payment (booking_id, amount, method, status, paid_at)
        VALUES (%s, %s, %s, 'SUCCESS', NOW())
        RETURNING payment_id
    """, (booking_id, total, payment_method))
    payment_id = cur.fetchone()[0]
    
    # 9. Update booking to CONFIRMED
    cur.execute("""
        UPDATE Booking SET status = 'CONFIRMED' WHERE booking_id = %s
    """, (booking_id,))
    
    # Return booking details
    return {
        "booking_id": booking_id,
        "customer_id": customer_id,
        "show_id": show_id,
        "total_amount": total,
        "status": "CONFIRMED",
        "tickets": seat_details,
        "payment_id": payment_id
    }
