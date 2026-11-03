from datetime import datetime, timedelta

def cancel_booking(cur, customer_id: int, booking_id: int):
    """
    Atomic cancellation transaction:
    1. Validate booking belongs to user and is CONFIRMED
    2. Check show is > 2 hours away
    3. Update booking to CANCELLED
    4. Update tickets to CANCELLED
    5. Update payment to REFUNDED
    6. Commit
    """
    
    # 1. Validate booking
    cur.execute("""
        SELECT b.booking_id, b.customer_id, b.show_id, b.status, b.total_amount,
               s.show_date, s.start_time
        FROM Booking b
        JOIN "show" s ON b.show_id = s.show_id
        WHERE b.booking_id = %s
    """, (booking_id,))
    booking = cur.fetchone()
    
    if not booking:
        raise ValueError("Booking not found")
    
    b_id, b_customer_id, show_id, status, total_amount, show_date, start_time = booking
    
    if b_customer_id != customer_id:
        raise ValueError("Not authorized to cancel this booking")
    
    if status != 'CONFIRMED':
        raise ValueError("Only confirmed bookings can be cancelled")
    
    # 2. Check show is > 2 hours away
    show_datetime = datetime.combine(show_date, start_time)
    if show_datetime <= datetime.now() + timedelta(hours=2):
        raise ValueError("Cannot cancel: show starts in less than 2 hours")
    
    # 3. Update booking to CANCELLED
    cur.execute("""
        UPDATE Booking SET status = 'CANCELLED' WHERE booking_id = %s
    """, (booking_id,))
    
    # 4. Update tickets to CANCELLED
    cur.execute("""
        UPDATE Ticket SET status = 'CANCELLED' WHERE booking_id = %s
    """, (booking_id,))
    
    # 5. Update payment to REFUNDED
    cur.execute("""
        UPDATE Payment SET status = 'REFUNDED' WHERE booking_id = %s
    """, (booking_id,))
    
    return {
        "booking_id": booking_id,
        "status": "CANCELLED",
        "refunded_amount": total_amount,
        "payment_status": "REFUNDED"
    }
