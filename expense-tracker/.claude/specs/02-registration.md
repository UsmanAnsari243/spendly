# Spec: Registration

## Overview

Turn the stub `GET /register` page into a working sign-up flow. A visitor submits their name, email and password; the app validates the input, stores a new user with a hashed password, and redirects them to the login page. This is the first half of authentication and gives later steps (login/logout, profile, expenses) real users to work with beyond the seeded demo user.

## Depends on

- Step 01 — Database setup (`users` table, `get_db()`, `init_db()`).

## Routes

- GET /register — render the registration form — public
- POST /register — validate the form, create the user, redirect to `/login` on success; re-render the form with an error message on failure — public

(`/register` already exists as a GET-only stub in `app.py`; it becomes `methods=["GET", "POST"]`.)

## Database changes

No database changes. The existing `users` table already has `name`, `email` (UNIQUE, NOT NULL), `password_hash` and `created_at`.

Add one helper to `database/db.py`:

- `create_user(name, email, password)` — hashes the password with `generate_password_hash`, inserts the row with a parameterised query, and returns the new user id. A duplicate email must surface as `sqlite3.IntegrityError`, which the route catches. Always closes its connection.

## Templates

- Create: none
- Modify:
  - `templates/register.html`
    - Change `action="/register"` to `action="{{ url_for('register') }}"` (no hardcoded URLs).
    - Re-populate the `name` and `email` fields with the submitted values after a failed submit (never re-populate the password).
    - Add `minlength="8"` to the password input to match the placeholder.
    - Keep the existing `{% if error %}` block for error display.

## Files to change

- `app.py` — accept POST on `/register`, validation, call `create_user`, redirect, handle duplicate email
- `database/db.py` — add `create_user()`
- `templates/register.html` — see above

## Files to create

- None (a test file is optional; see Definition of done)

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (`generate_password_hash`); never store or log the plain password
- Use CSS variables — never hardcode hex values (reuse the existing `.auth-*` and `.form-*` classes; add nothing unless needed)
- All templates extend base.html
- DB logic lives in `database/db.py` only; the route just reads the form, calls the helper, and renders or redirects
- Use `url_for()` for every link and redirect
- Validation (server-side, in this order), re-rendering `register.html` with an `error` and HTTP 400:
  - name: required, trimmed, non-empty
  - email: required, trimmed, lower-cased, must contain `@` with text on both sides
  - password: required, at least 8 characters
  - email already registered: "An account with that email already exists."
- Rely on the UNIQUE constraint via `IntegrityError` rather than a check-then-insert, to avoid a race
- Do not add sessions, `secret_key`, flash messages or auto-login here; that belongs to Step 3 (login/logout)
- Do not change the port (5001)

## Definition of done

- [ ] `GET /register` renders the form and the form posts to `/register` via `url_for`
- [ ] Submitting valid, new details creates a row in `users` and redirects (302) to `/login`
- [ ] The stored `password_hash` is a werkzeug hash, not the plain password
- [ ] Email is stored trimmed and lower-cased
- [ ] Registering `demo@spendly.com` (or any existing email, in any letter case) shows the "already exists" error and creates no second row
- [ ] Blank name, invalid email, or password under 8 characters each shows an error and creates no row
- [ ] After a failed submit, name and email are pre-filled and the password field is empty
- [ ] Error responses return HTTP 400; success never returns 200 with the form
- [ ] A user created via the form can later be found with `SELECT` by email and has no expenses
- [ ] App starts on port 5001 with no errors and the other pages (`/`, `/login`, `/terms`, `/privacy`) still render
