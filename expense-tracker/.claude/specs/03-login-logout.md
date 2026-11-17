# Spec: Login and Logout

## Overview

Turn the stub login and logout pages into a working session flow. A registered user submits their email and password; the app verifies the hash, stores `user_id` in a signed Flask session cookie, and redirects them to `/profile`. Logging out clears the session and returns them to the landing page. This is the second half of authentication (Step 02 created the users) and gives Step 04 (profile) and the expense steps a way to know who is making each request. The navbar also changes to reflect logged-in state.

## Depends on

- Step 01 — Database setup (`users` table, `get_db()`).
- Step 02 — Registration (`create_user()`, users with werkzeug password hashes; successful registration already redirects to `/login`).

## Routes

- GET /login — render the sign-in form; redirect to `/profile` if already logged in — public
- POST /login — verify credentials; on success reset the session, set `session["user_id"]`, redirect to `/profile`; on failure re-render the form with an error and HTTP 400 — public
- GET /logout — clear the session and redirect to `/` — public (harmless when already logged out)

(`/login` is currently GET-only and `/logout` is a placeholder string stub in `app.py`; both are replaced, not duplicated. `/profile` stays a stub until Step 04.)

## Database changes

No database changes. The `users` table already has everything needed.

Add one helper to `database/db.py`:

- `get_user_by_email(email)` — parameterised `SELECT id, name, email, password_hash FROM users WHERE email = ?`; returns a `sqlite3.Row` or `None`; always closes its connection. For authentication only; the row (with its hash) must never be passed to a template.

## Templates

- Create: none
- Modify:
  - `templates/login.html`
    - Change `action="/login"` to `action="{{ url_for('login') }}"` (no hardcoded URLs).
    - Re-populate the `email` field with the submitted value after a failed submit (never the password).
    - Keep the existing `{% if error %}` block.
  - `templates/base.html`
    - When logged in, show "Profile" (`url_for('profile')`) and "Sign out" (`url_for('logout')`) in place of "Sign in" / "Get started".
    - When logged out, keep the existing "Sign in" / "Get started" links.
    - Driven by a `logged_in` boolean supplied by a context processor (see Rules).
  - `templates/landing.html` — only if it contains hardcoded login/register URLs or a "get started" CTA that should hide when logged in; use `url_for()` either way.

## Files to change

- `app.py` — import `session`, `check_password_hash`, `get_user_by_email`; set `app.secret_key`; implement `login()` GET/POST and `logout()`; remove the duplicate placeholder `logout`; add the context processor
- `database/db.py` — add `get_user_by_email()`
- `templates/login.html` — see above
- `templates/base.html` — conditional nav links
- `templates/landing.html` — only if needed (see above)
- `tests/test_register.py` — only if existing tests break because of the new session behaviour

## Files to create

- `tests/test_login.py` — successful login redirects to `/profile` and sets the session; wrong password and unknown email both return 400 with the identical message; email is case-insensitive and trimmed; logged-in GET `/login` redirects to `/profile`; `/logout` clears the session; navbar shows the correct links in each state
- `tests/conftest.py` — only if one does not already exist: an `app`/`client` fixture using a temporary database (patch `DB_PATH`), so tests never touch `spendly.db`

## New dependencies

No new dependencies. Flask's built-in `session` and werkzeug's `check_password_hash` are already available.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug; verify with `check_password_hash`, never compare plain text, never log or echo the password
- Use CSS variables — never hardcode hex values (reuse the existing `.auth-*`, `.form-*` and navbar classes; add nothing unless needed, and any new rule goes in an existing stylesheet, not an inline `<style>`)
- All templates extend base.html
- DB logic lives in `database/db.py` only; the route reads the form, calls the helper, verifies the hash, and redirects or renders
- Use `url_for()` for every link and redirect
- `app.secret_key` read from the `SECRET_KEY` environment variable with a clearly-labelled development fallback; never a value that looks production-ready committed to the repo
- Normalise email (strip, lower-case) before lookup, matching registration
- Use one generic message, "Invalid email or password.", for both unknown email and wrong password, so accounts cannot be enumerated
- Call `session.clear()` before setting `user_id` on login (prevents session fixation); store only `user_id` in the session, nothing else
- Failed login returns HTTP 400 (consistent with registration), success returns a 302
- Logged-in state is exposed to templates through a single `@app.context_processor` returning `logged_in`; templates do not read `session` directly
- Do not implement `/profile` here; the existing stub remains until Step 04
- Do not add flash messages, "remember me", password reset or rate limiting
- Do not change the port (5001)

## Definition of done

- [ ] `GET /login` renders the form and the form posts to `/login` via `url_for`
- [ ] Logging in as `demo@spendly.com` / `demo123` returns 302 to `/profile` and sets a session cookie
- [ ] A wrong password and an unknown email both show exactly "Invalid email or password." with HTTP 400
- [ ] Email is matched trimmed and case-insensitively (`  Demo@Spendly.com ` works)
- [ ] After a failed submit the email is pre-filled and the password field is empty
- [ ] A user created through `/register` can log in immediately with the same credentials
- [ ] While logged in, `GET /login` redirects to `/profile`
- [ ] `GET /logout` returns 302 to `/`, and the session no longer contains `user_id`
- [ ] Navbar shows "Profile" and "Sign out" when logged in, and "Sign in" and "Get started" when logged out, on every page
- [ ] No password hash appears in any rendered page source
- [ ] There is exactly one `logout` route in `app.py` and no raw-string stub returns for login/logout
- [ ] `pytest` passes, including the new login tests
- [ ] App starts on port 5001 with no errors and `/`, `/register`, `/terms`, `/privacy` still render
