# Spec: Add Expense

## Overview
Step 7 lets a logged-in user record a new expense (amount in PKR, category, date and an optional description) through a form, and have it appear on their profile page. It replaces the raw-string stub for `/expenses/add`, which the profile page's "Add your first expense" button already links to. It is the first write path for the `expenses` table beyond seed data, and it unblocks edit (Step 8) and delete (Step 9).

## Depends on
- Step 01 — Database setup (`expenses` table, `get_db()`, `CATEGORIES`)
- Step 03 — Login / logout (`session["user_id"]`, `load_session_user()`)
- Step 04/05 — Profile page (where the new expense is displayed and where the user is redirected)

## Routes
- GET /expenses/add — render the empty add-expense form (date defaults to today) — logged-in
- POST /expenses/add — validate and insert the expense, then redirect to `url_for("profile")` — logged-in

Logged-out users are redirected to login via the existing `load_session_user()` behaviour. No other new routes. The edit and delete stubs stay as they are.

## Database changes
No database changes. The existing `expenses` table (`id`, `user_id`, `amount`, `category`, `date`, `description`, `created_at`) is sufficient. There are no CHECK constraints, so all validation lives in the app.

New helper in `database/db.py`:
- `create_expense(user_id, amount, category, date, description=None)` — inserts one row using a parameterised query inside `with conn:`, closes the connection in `finally`, and returns the new row id.

## Templates
- Create: `templates/add_expense.html` — extends `base.html`; reuses the existing `auth-section` / `auth-card` / `form-group` / `form-input` / `btn-submit` / `auth-error` pattern from `profile_edit.html`. Fields:
  - Amount (`type="number"`, `step="0.01"`, `min="0.01"`, labelled "Amount (PKR)")
  - Category (`<select>` populated from `categories`)
  - Date (`type="date"`, `max` set to today)
  - Description (optional text, `maxlength="200"`)
  - A Cancel link back to the profile page using `url_for`
- Modify: `templates/base.html` — add an "Add expense" nav link, shown only when `logged_in`, using `url_for('add_expense')`.

## Files to change
- `app.py` — replace the `add_expense` stub (GET and POST), pass `categories` and today's date to the template, add a small validation helper alongside the existing `validate_name_email` / `parse_period` helpers
- `database/db.py` — add `create_expense()`
- `templates/base.html` — nav link

## Files to create
- `templates/add_expense.html`
- `static/css/expense.css` — page-specific styles only (e.g. the category select and two-column amount/date row), loaded through the `head` block
- `tests/test_add_expense.py`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (not touched by this step; do not alter existing auth)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Use `url_for()` for every link and redirect — never hardcode URLs
- DB logic goes in `database/db.py` only; the route fetches/validates, calls the helper, redirects
- Never insert for a user other than `session["user_id"]`; ignore any `user_id` in the form data
- Validation (server side, regardless of HTML attributes):
  - amount: parseable as a number, finite, greater than 0, at most 2 decimal places, and below a sane maximum (e.g. 10,000,000)
  - category: must be one of `db.CATEGORIES`
  - date: valid ISO `YYYY-MM-DD` (use `date.fromisoformat`) and not in the future
  - description: optional, stripped, at most 200 characters; store `None` when empty
- On validation failure return HTTP 400 using the existing `form_error`-style pattern: re-render `add_expense.html` with `error` and every submitted value echoed back
- On success redirect (POST/redirect/GET) to `url_for("profile")`; no flash mechanism exists, so do not add one
- Use `abort()` for HTTP errors, not raw string returns; the stub's raw string return must be removed
- Currency is PKR everywhere — never INR or USD
- Vanilla JS only; no JS is required for this step
- Keep the app on port 5001

## Definition of done
- [ ] Visiting `/expenses/add` while logged out redirects to the login page
- [ ] Visiting `/expenses/add` while logged in shows the form with Amount (PKR), Category, Date (defaulting to today) and Description
- [ ] The category dropdown lists exactly the seven values in `db.CATEGORIES`
- [ ] Submitting a valid expense redirects to `/profile`, and the expense appears in the recent list and is reflected in the totals and category breakdown
- [ ] A new expense is stored against the logged-in user's id and is not visible to other users
- [ ] Submitting with an empty or non-numeric amount, an amount of 0 or less, or more than 2 decimal places shows an error and returns 400 with the other fields preserved
- [ ] Submitting a category not in `CATEGORIES` returns 400
- [ ] Submitting a malformed date or a future date returns 400
- [ ] A description over 200 characters returns 400; an empty description saves successfully with `NULL`
- [ ] The "Add your first expense" button on the empty profile state now opens the form
- [ ] The "Add expense" nav link appears only when logged in
- [ ] `pytest` passes, including new tests in `tests/test_add_expense.py` covering auth redirect, GET render, successful insert, each validation failure, and per-user isolation
