# Customer templates: notes for the backend

The templates in `backend/app/templates/` are built against the page routes in
`backend/main.py` as of commit a22903e. They use the route function names
with `url_for` (`index`, `movies_page`, `movie_detail`, `seat_select`,
`book_seats`, `checkout_page`, `process_booking`, `confirmation`,
`my_bookings`, `cancel_booking`, `login_page`, `login_submit`,
`register_page`, `register_submit`, `logout`), so **renaming a route function
breaks the links to it**. Static files are linked with
`url_for('static', path=...)`.

To check a page without a database, run `python app/preview.py` from
`backend/` (see the top of that file). It copies main.py's routes and
variables with fake data, so keep it in step when main.py changes.

## Changes needed in main.py

1. **Payment method on the checkout page.** Right now `book_seats` requires
   `payment_method`, so the seat page asks for it, and the checkout page only
   shows it. Your old checkout radios were ignored by `/book`. If `/book` reads
   `payment_method: str = Form("UPI")` (the checkout form already posts it)
   and `book_seats` makes it optional, I'll move the choice to checkout.
2. **`seats_left` on each show** in `movie_detail` (ATK's `get_seats_left()`).
   The template shows "N seats left" and "Sold out" as soon as it's there,
   and the end time until then.
3. **`can_cancel` on each booking** in `my_bookings` (CONFIRMED and show more
   than 2 hours away). Until then the Cancel button shows on every confirmed
   booking, and late cancels are refused by the server with a flash message.
4. **`languages`** (all distinct movie languages) in `movies_page`. Until then
   the dropdown lists the languages of the movies on the current page.
5. **404 and 500 handlers** that render `404.html` and `error.html` with
   `{"user": ...}`. Right now a missing movie or booking returns FastAPI's
   JSON error. `preview.py` has working handlers you can copy.
6. **Readable booking errors.** `create_booking` raises
   `Seat(s) [5] already booked`; the contract had `Seat A-5 just taken, please
   select another`. The message is shown to the user as is.
7. **Don't flash raw exceptions.** `flash(request, str(e), "error")` in
   `process_booking` and `cancel_booking` would show database errors to users.
   Flash only `ValueError` messages and a generic message for anything else.
8. Remove the debug `print` in `flash_context_processor`.

## Things in the repo (not templates)

- `backend/requirements.txt` is missing, so the README's install step fails.
- This branch adds `backend/app/static/`. Without it `StaticFiles` stops the
  app from starting on a fresh clone.
- `POST /auth/register` in the API contract accepts `role: ADMIN`. The HTML
  register route correctly forces CUSTOMER.

## Assumptions the templates make

- Flash categories: `success`, `error`, `warning`, anything else shows blue.
- `user` is None or a dict with `name` and `role`. ADMIN users get an Admin
  link to `/admin` (plain path until ATK's admin route exists).
- Dates, times and datetimes can be Python objects or strings; both render as
  `YYYY-MM-DD`, `HH:MM` and `YYYY-MM-DD HH:MM`.
- Seat `status` is compared case-insensitively; anything but `available` is
  shown as taken.
- In `confirmation`, `seats`, `seat_categories` and `prices` are parallel
  lists. Each `STRING_AGG` should use the same `ORDER BY` (for example
  `ORDER BY st.row_label, st.seat_number`) so they stay lined up.
- The 6-seat limit is enforced only in `seats.js`; `book_seats` should
  reject more than 6 too.
