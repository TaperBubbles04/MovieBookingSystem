# Customer templates: notes for the backend

The templates in `backend/app/templates/` use the page route function names in
`backend/main.py` with `url_for` (`index`, `movies_page`, `movie_detail`,
`seat_select`, `book_seats`, `checkout_page`, `process_booking`,
`confirmation`, `my_bookings`, `cancel_booking`, `login_page`, `login_submit`,
`register_page`, `register_submit`, `logout`), so **renaming a route function
breaks the links to it**. Static files are linked with
`url_for('static', path=...)`.

To check a customer page without a database, run `python app/preview.py` from
`backend/` (see the top of that file). It copies main.py's customer routes and
variables with fake data, so keep it in step when main.py changes.

## Open items

### Database (db/)

1. **All seeded shows are in the past.** `db/seed.sql` here has fixed dates
   from 2026-10-27 to 2026-11-02, so every movie shows "No shows are scheduled"
   and nothing can be booked. The `Movie-Booking-System` repo has a later seed
   with relative dates (commit 3d9b04e) that did not make it into this repo.

### main.py

2. **Admin pages look unstyled.** `admin.html` and `admin_reports.html` use
   Tailwind classes, but `base.html` only loads Bootstrap.
3. **Second flash message is lost.** `flash()` calls `.append()` on the list
   already in the session, and the session middleware does not save in-place
   changes. If a message is still pending, the new one disappears. Assign a new
   list instead: `request.session["_flashes"] = existing + [new]`.
4. **Readable booking errors.** `create_booking` raises
   `Seat(s) [5] already booked`, and that text is shown to the user. The
   contract has `Seat A-5 just taken, please select another`.
5. **Seat order on the ticket.** In `confirmation`, `seats`, `seat_categories`
   and `prices` are parallel lists. Each `STRING_AGG` should use the same
   `ORDER BY st.row_label, st.seat_number` so they stay lined up. The
   `my_bookings` query should use it too.
6. **Error handlers come after `uvicorn.run`.** They are registered below the
   `if __name__ == "__main__"` block, so `python main.py` runs without them.
   `uvicorn main:app` is fine. Move them above that block.
7. **Error page when the database is down.** The 500 handler calls
   `get_current_user`, which needs the database, so it can fail while handling
   a database failure.

### Docs and templates

8. **API contract.** `POST /auth/register` in `docs/api_contract.md` still
   accepts `role: ADMIN`. The HTML register route correctly forces CUSTOMER.
9. **Home page data.** `index` sends `genres` and `featured_movies`, but
   `index.html` doesn't show them yet.

## Assumptions the templates make

- Flash categories: `success`, `error`, `warning`, anything else shows blue.
- `user` is None or a dict with `name` and `role`. ADMIN users get a link to
  `/admin`.
- Dates, times and datetimes can be Python objects or strings; both render as
  `YYYY-MM-DD`, `HH:MM` and `YYYY-MM-DD HH:MM`.
- Seat `status` is compared case-insensitively; anything but `available` is
  shown as taken.
- The checkout form posts `payment_method`; seats stay in the session.
