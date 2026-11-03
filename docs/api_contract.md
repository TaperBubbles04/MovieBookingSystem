# CineBook API Contract v1.0

**Version:** 1.0  
**Last Updated:** 2026-10-30  
**Status:** Draft - Pending Team Review

---

## 📋 General Rules

| Aspect | Convention |
|--------|------------|
| **Format** | JSON request/response bodies |
| **Dates** | `YYYY-MM-DD` (ISO 8601 date) |
| **Times** | `HH:MM` (24-hour format) |
| **Money** | Integer rupees (e.g., `150` = ₹150) |
| **Auth** | Bearer JWT in `Authorization` header |
| **Error Format** | `{"detail": "Human-readable message", "code": "ERROR_CODE"}` |
| **Success** | HTTP 200/201 with data; HTTP 204 for empty success |

---

## 🔐 Auth Module

### POST /auth/register
**Access:** Public  
**Request:**
```json
{
  "name": "string (required, 1-100)",
  "email": "string (required, valid email, unique)",
  "phone": "string (required, unique, 10 digits)",
  "password": "string (required, min 8 chars)",
  "role": "string (optional, default: CUSTOMER, enum: [CUSTOMER, ADMIN])"
}
```
**Response 201:**
```json
{
  "user": {
    "customer_id": 1,
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "9876543210",
    "role": "CUSTOMER",
    "created_at": "2026-10-30T10:30:00Z"
  },
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```
**Errors:**
- 400: `{"detail": "Email already registered", "code": "EMAIL_EXISTS"}`
- 400: `{"detail": "Phone already registered", "code": "PHONE_EXISTS"}`
- 422: Validation error

---

### POST /auth/login
**Access:** Public  
**Request:**
```json
{
  "email": "string (required)",
  "password": "string (required)"
}
```
**Response 200:**
```json
{
  "user": { "customer_id": 1, "name": "John", "email": "...", "phone": "...", "role": "CUSTOMER" },
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```
**Errors:**
- 401: `{"detail": "Invalid credentials", "code": "INVALID_CREDENTIALS"}`
- 422: Validation error

---

### GET /auth/me
**Access:** Authenticated (Customer/Admin)  
**Headers:** `Authorization: Bearer <token>`  
**Response 200:**
```json
{
  "customer_id": 1,
  "name": "John Doe",
  "email": "john@example.com",
  "phone": "9876543210",
  "role": "CUSTOMER",
  "created_at": "2026-10-30T10:30:00Z"
}
```
**Errors:**
- 401: `{"detail": "Invalid or expired token", "code": "UNAUTHORIZED"}`

---

## 🎬 Movies Module

### GET /movies
**Access:** Public  
**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `search` | string | Partial title match (ILIKE) |
| `genre` | string | Filter by genre name |
| `language` | string | Filter by language |
| `certificate` | string | Filter: U, UA, A |
| `min_rating` | float | Minimum rating (0-10) |
| `limit` | int | Default 20, max 100 |
| `offset` | int | Default 0 |

**Response 200:**
```json
{
  "movies": [
    {
      "movie_id": 1,
      "title": "Inception",
      "description": "A thief who steals corporate secrets...",
      "duration_min": 148,
      "language": "English",
      "certificate": "UA",
      "release_date": "2010-07-16",
      "rating": 8.8,
      "poster_url": "https://...",
      "genres": ["Action", "Sci-Fi", "Thriller"]
    }
  ],
  "total": 42,
  "limit": 20,
  "offset": 0
}
```

---

### GET /movies/{movie_id}
**Access:** Public  
**Response 200:** (same movie object as above with full details)  
**Errors:**
- 404: `{"detail": "Movie not found", "code": "NOT_FOUND"}`

---

### POST /movies
**Access:** Admin only  
**Request:**
```json
{
  "title": "string (required, 1-200)",
  "description": "string (optional)",
  "duration_min": "int (required, > 0)",
  "language": "string (required)",
  "certificate": "string (required, enum: [U, UA, A])",
  "release_date": "date (required, YYYY-MM-DD)",
  "rating": "float (optional, 0-10)",
  "poster_url": "string (optional, URL)",
  "genre_ids": "int[] (optional, array of genre_ids)"
}
```
**Response 201:** Full movie object with genres  
**Errors:**
- 401/403: Unauthorized/Admin required
- 422: Validation error (certificate, duration, rating bounds)

---

### PUT /movies/{movie_id}
**Access:** Admin only  
**Request:** Same as POST (all fields optional for partial update)  
**Response 200:** Updated movie object  
**Errors:** 401/403, 404, 422

---

### DELETE /movies/{movie_id}
**Access:** Admin only  
**Response 204:** No content  
**Errors:**
- 401/403
- 404: Not found
- 409: `{"detail": "Cannot delete movie with scheduled shows", "code": "HAS_SHOWS"}`

---

## 🎭 Genres Module

### GET /genres
**Access:** Public/Admin  
**Response 200:**
```json
{ "genres": [{ "genre_id": 1, "genre_name": "Action" }, ...] }
```

### POST /genres
**Access:** Admin only  
**Request:** `{ "genre_name": "string (required, unique)" }`  
**Response 201:** Created genre object  
**Errors:** 401/403, 409 (duplicate)

---

## 🏢 Theatres Module

### GET /theatres
**Access:** Public  
**Response 200:**
```json
{
  "theatres": [
    {
      "theatre_id": 1,
      "name": "PVR Phoenix",
      "city": "Chennai",
      "address": "Velachery, Chennai"
    }
  ]
}
```

---

### POST /theatres
**Access:** Admin only  
**Request:**
```json
{
  "name": "string (required)",
  "city": "string (required)",
  "address": "string (required)"
}
```
**Response 201:** Created theatre object  
**Errors:** 401/403, 422

---

### POST /theatres/{theatre_id}/screens
**Access:** Admin only  
**Request:**
```json
{
  "screen_name": "string (required, unique per theatre)",
  "screen_type": "string (required, enum: [2D, 3D, IMAX])",
  "rows": "string (required, e.g., 'A,B,C,D,E,F,G,H')",
  "seats_per_row": "int (required, > 0)",
  "premium_rows": "string (optional, e.g., 'G,H' - last rows)",
  "recliner_rows": "string (optional, e.g., 'H' - back row)"
}
```
**Response 201:**
```json
{
  "screen_id": 1,
  "theatre_id": 1,
  "screen_name": "Screen 1",
  "screen_type": "IMAX",
  "seats_created": 120,
  "seat_layout": {
    "REGULAR": 80,
    "PREMIUM": 30,
    "RECLINER": 10
  }
}
```
**Logic:** Auto-generates Seat rows from `rows` and `seats_per_row`. Last rows → PREMIUM, back row → RECLINER.  
**Errors:** 401/403, 404 (theatre), 409 (screen_name duplicate), 422

---

## 🎥 Shows Module

### GET /shows
**Access:** Public  
**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `movie_id` | int | Filter by movie |
| `date` | date | Filter by show_date (YYYY-MM-DD) |
| `city` | string | Filter by theatre city |
| `limit` | int | Default 20 |
| `offset` | int | Default 0 |

**Response 200:**
```json
{
  "shows": [
    {
      "show_id": 1,
      "movie": { "movie_id": 1, "title": "Inception", "duration_min": 148, "poster_url": "..." },
      "theatre": { "theatre_id": 1, "name": "PVR Phoenix", "city": "Chennai" },
      "screen": { "screen_id": 1, "screen_name": "Screen 1", "screen_type": "IMAX" },
      "show_date": "2026-11-01",
      "start_time": "19:30",
      "end_time": "22:00"
    }
  ],
  "total": 15
}
```

---

### GET /shows/{show_id}
**Access:** Public  
**Response 200:** Full show object with movie, theatre, screen, pricing  
**Errors:** 404

---

### GET /shows/{show_id}/seats
**Access:** Public  
**Response 200:**
```json
{
  "show_id": 1,
  "screen": { "screen_id": 1, "screen_name": "Screen 1", "screen_type": "IMAX" },
  "seats": [
    {
      "seat_id": 1,
      "row_label": "A",
      "seat_number": 1,
      "seat_category": "REGULAR",
      "price": 180,
      "status": "available"
    },
    {
      "seat_id": 5,
      "row_label": "A",
      "seat_number": 5,
      "seat_category": "REGULAR",
      "price": 180,
      "status": "taken"
    }
  ],
  "summary": { "total": 120, "available": 95, "taken": 25 }
}
```
**Logic:** `status = "taken"` if active ticket exists for this show_id + seat_id; else `"available"`

---

### POST /shows
**Access:** Admin only  
**Request:**
```json
{
  "movie_id": 1,
  "screen_id": 1,
  "show_date": "2026-11-01",
  "start_time": "19:30",
  "end_time": "22:00"
}
```
**Response 201:** Created show object  
**Errors:**
- 401/403
- 409: `{"detail": "Overlapping show on this screen", "code": "OVERLAP"}`
- 422: Validation (end_time > start_time, valid movie/screen)

---

### PUT /shows/{show_id}/pricing
**Access:** Admin only  
**Request:**
```json
{
  "pricing": [
    { "seat_category": "REGULAR", "price": 180 },
    { "seat_category": "PREMIUM", "price": 250 },
    { "seat_category": "RECLINER", "price": 400 }
  ]
}
```
**Response 200:** Updated show with pricing  
**Errors:** 401/403, 404, 422 (price >= 0, valid categories)

---

## 🎟️ Bookings Module

### POST /bookings
**Access:** Authenticated (Customer)  
**Request:**
```json
{
  "show_id": 1,
  "seat_ids": [5, 6, 7],
  "payment_method": "UPI"
}
```
**Response 201:**
```json
{
  "booking": {
    "booking_id": 101,
    "customer_id": 1,
    "show_id": 1,
    "booking_time": "2026-10-30T10:30:00Z",
    "total_amount": 540,
    "status": "CONFIRMED"
  },
  "tickets": [
    { "ticket_id": 1, "seat_id": 5, "price": 180, "status": "ACTIVE" },
    { "ticket_id": 2, "seat_id": 6, "price": 180, "status": "ACTIVE" },
    { "ticket_id": 3, "seat_id": 7, "price": 180, "status": "ACTIVE" }
  ],
  "payment": {
    "payment_id": 1,
    "amount": 540,
    "method": "UPI",
    "status": "SUCCESS",
    "paid_at": "2026-10-30T10:30:00Z"
  }
}
```
**Transaction:** Atomic - validates seats belong to show's screen, locks seats (FOR UPDATE), checks no active tickets, calculates total from Show_Pricing, inserts booking + tickets + payment, commits.
**Errors:**
- 401: Unauthorized
- 404: Show not found
- 409: `{"detail": "Seat A-5 just taken, please select another", "code": "SEAT_TAKEN", "seat_id": 5}`
- 400: Invalid seats (not in show's screen), show already started
- 422: Validation

---

### GET /bookings/me
**Access:** Authenticated (Customer)  
**Query:** `limit`, `offset`  
**Response 200:**
```json
{
  "bookings": [
    {
      "booking_id": 101,
      "show_id": 1,
      "movie": { "title": "Inception", "poster_url": "..." },
      "theatre": { "name": "PVR Phoenix", "city": "Chennai" },
      "screen": { "screen_name": "Screen 1" },
      "show_date": "2026-11-01",
      "start_time": "19:30",
      "total_amount": 540,
      "status": "CONFIRMED",
      "seats": ["A-5", "A-6", "A-7"],
      "booking_time": "2026-10-30T10:30:00Z"
    }
  ],
  "total": 5
}
```

---

### GET /bookings/{booking_id}
**Access:** Authenticated (Owner or Admin)  
**Response 200:** Full booking with tickets (seat labels, prices), payment details  
**Errors:** 401/403 (not owner), 404

---

### POST /bookings/{booking_id}/cancel
**Access:** Authenticated (Customer - owner only)  
**Response 200:**
```json
{
  "booking_id": 101,
  "status": "CANCELLED",
  "tickets_cancelled": 3,
  "refunded_amount": 540,
  "payment_status": "REFUNDED"
}
```
**Transaction:** Atomic - validates ownership, status=CONFIRMED, show > 2 hours away. Updates booking→CANCELLED, tickets→CANCELLED, payment→REFUNDED.
**Errors:**
- 401/403: Not owner
- 400: Already cancelled
- 409: `{"detail": "Cannot cancel: show starts in less than 2 hours", "code": "TOO_LATE"}`
- 404: Not found

---

## 📊 Reports Module (Admin Only)

### GET /reports/revenue-by-movie
**Access:** Admin  
**Query:** `date_from`, `date_to` (optional, default last 30 days)  
**Response 200:**
```json
{
  "report": [
    { "movie_id": 1, "title": "Inception", "total_revenue": 125000, "tickets_sold": 450, "avg_price": 278 }
  ]
}
```

---

### GET /reports/occupancy
**Access:** Admin  
**Query:** `date_from`, `date_to`, `theatre_id` (optional)  
**Response 200:**
```json
{
  "report": [
    {
      "show_id": 1,
      "movie": "Inception",
      "theatre": "PVR Phoenix",
      "screen": "Screen 1",
      "show_date": "2026-11-01",
      "total_seats": 120,
      "booked_seats": 95,
      "occupancy_pct": 79.2
    }
  ]
}
```

---

### GET /reports/top-customers
**Access:** Admin  
**Query:** `limit` (default 10), `date_from`, `date_to`  
**Response 200:**
```json
{
  "report": [
    { "customer_id": 1, "name": "John Doe", "email": "...", "total_spent": 5000, "bookings_count": 8 }
  ]
}
```

---

### GET /reports/daily-sales
**Access:** Admin  
**Query:** `days` (default 7)  
**Response 200:**
```json
{
  "report": [
    { "date": "2026-10-25", "revenue": 45000, "bookings": 12 },
    { "date": "2026-10-26", "revenue": 52000, "bookings": 15 }
  ]
}
```

---

### GET /reports/unsold-movies
**Access:** Admin  
**Response 200:**
```json
{
  "report": [
    { "movie_id": 5, "title": "Movie With No Shows", "language": "Tamil", "certificate": "U" }
  ]
}
```

---

## 📝 Notes for Frontend Integration

1. **Seat Map Colors:** available=green, selected=blue, taken=red, premium=gold, recliner=purple
2. **Error Handling:** Always show `detail` message to user; `code` for programmatic handling
3. **Loading States:** All list endpoints support pagination
4. **Auth Storage:** Store JWT in memory/localStorage; redirect to login on 401
5. **Admin Routes:** Check `user.role === 'ADMIN'` before rendering admin UI

---

## ✅ Team Sign-off

| Role | Name | Approved | Date |
|------|------|----------|------|
| Backend (Tharanesh) | | ☐ | |
| Frontend (Mohit) | | ☐ | |
| Admin/Data (ATK) | Yashvant A T K | ☑ | 2026-10-31 |

---
