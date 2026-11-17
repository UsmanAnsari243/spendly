# Spec: Backend Routes for Profile Page

## Overview

Step 04 gave the profile page a read-only view of the user's data. This step adds the backend routes that let a logged-in user manage their own account from that page: edit their name and email, and change their password. These are the first routes that write to the `users` table after registration, and they finish the profile page's backend before the expense create/edit/delete steps (7-9) begin.

Scope decision: the read side of `/profile` (summary, breakdown, recent list, `?from=&to=` period filter) already exists and is not changed here. Account deletion, filter presets and flash messages are deliberately out of scope.

## Depends on

- Step 01 - Database setup (`users` table, `get_db()`).
- Step 02 - Registration (email normalisation and validation rules, `IntegrityError` on duplicate email).
- Step 03 - Login and logout (`session["user_id"]`, `check_password_hash`, `inject_auth_state`).
- Step 04 - Profile page (`/profile`, `get_user_by_id()`, `templates/profile.html`, `static/css/profile.css`).

## Routes

- GET /profile/edit - render the edit form pre-filled with the current name and email; redirect to `/login` if not logged in; `abort(404)` if the session user no longer exists - logged-in
- POST /profile/edit - validate and update name and email; on success redirect (302) to `/profile`; on validation failure re-render the form with an error, the submitted values, and HTTP 400; on duplicate email re-render with "An account with that email already exists." and HTTP 400 - logged-in
- GET /profile/password - render the change-password form; redirect to `/login` if not logged in - logged-in
- POST /profile/password - verify the current password, validate the new one, update the hash; on success reset the session (keeping only `user_id`) and redirect (302) to `/profile`; on failure re-render with an error and HTTP 400 - logged-in

Logged-out requests to any of these four routes redirect (302) to `/login` and never touch the database.

## Database changes

No schema changes. The existing `users` table is sufficient.

Add these helpers to `database/db.py` (parameterised queries, always close the connection):

- `update_user(user_id, name, email)` - `UPDATE users SET name = ?, email = ? WHERE id = ?`; a duplicate email raises `sqlite3.IntegrityError` (same contract as `create_user`); returns `True` if a row was updated, else `False`.
- `get_password_hash(user_id)` - returns the stored `password_hash` string for that user, or `None`. For verification inside the route only; it must never be passed to a template.
- `update_password(user_id, new_password)` - hashes with `generate_password_hash` inside the helper and stores the result; returns `True` if a row was updated, else `False`.

## Templates

- Create:
  - `templates/profile_edit.html` - extends `base.html`; name and email fields, Save and Cancel (link back to `url_for('profile')`).
  - `templates/profile_password.html` - extends `base.html`; current password, new password, confirm new password fields.
- Modify:
  - `templates/profile.html` - add "Edit profile" and "Change password" links in the header using `url_for('edit_profile')` and `url_for('change_password')`.

Both new forms reuse the existing `.auth-*` / `.form-*` classes and the existing `{% if error %}` pattern from `login.html` and `register.html`. Forms post via `action="{{ url_for(...) }}"`.

## Files to change

- `app.py` - add `edit_profile()` and `change_password()` routes; import the new helpers; share the "current user or redirect/404" check with `profile()` rather than copying it a third time
- `database/db.py` - add `update_user()`, `get_password_hash()`, `update_password()`
- `templates/profile.html` - links to the two new pages
- `static/css/profile.css` - only for the new header links, if the existing classes are not enough

## Files to create

- `templates/profile_edit.html`
- `templates/profile_password.html`
- `tests/test_profile_edit.py` - see Definition of done; uses the existing `client`, `login` and `set_session_user` fixtures from `tests/conftest.py`

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug; verify with `check_password_hash`, hash with `generate_password_hash`; never compare, log, echo or re-render any password; never pass `password_hash` to a template
- Use CSS variables - never hardcode hex values
- All templates extend base.html
- DB logic lives in `database/db.py` only; routes read the form, call helpers, and redirect or render
- Use `url_for()` for every link and redirect; no hardcoded URLs
- Route function names are `edit_profile` and `change_password` (used by `url_for`)
- Reuse registration's rules exactly: name required (stripped); email stripped, lower-cased, must have text either side of an `@`; new password at least 8 characters
- The user id always comes from `session["user_id"]`, never from the form or URL, so a user can only change their own account
- Wrong current password and "new password equals current password" both fail with HTTP 400 and a specific message; the confirm field must match the new password
- On password change, call `session.clear()` and set `session["user_id"]` again (session rotation); store nothing else in the session
- Use `abort()` for HTTP errors, not raw strings
- Failed validation returns HTTP 400 and keeps the submitted name/email in the form (never any password field)
- No flash messages, email verification, password reset or rate limiting
- Do not change the existing `/profile` read behaviour or the period filter
- Do not change the port (5001)

## Definition of done

- [ ] Logged out, all four new routes (GET and POST) return 302 to `/login`
- [ ] Logged in, `GET /profile/edit` shows the current name and email pre-filled
- [ ] Submitting a new name and email returns 302 to `/profile`, and the profile page shows the new values
- [ ] Email is stored trimmed and lower-cased (`  New@Spendly.com ` becomes `new@spendly.com`)
- [ ] An empty name, a malformed email, or an email already used by another account each return 400 with the matching message and keep the typed values
- [ ] Re-saving your own unchanged email succeeds (it is not treated as a duplicate)
- [ ] `GET /profile/password` renders three password fields, none pre-filled
- [ ] A wrong current password, a new password under 8 characters, a mismatched confirmation, and a new password equal to the current one each return 400 with a distinct message
- [ ] A successful password change returns 302 to `/profile`; the old password no longer logs in and the new one does
- [ ] After a password change the session still contains only `user_id`
- [ ] User A's edit never changes User B's row (verified with two users)
- [ ] A session pointing at a deleted user gets 404 on the edit and password pages, not a 500
- [ ] No password hash or password value appears in any rendered page source
- [ ] The profile header links to both pages through `url_for`
- [ ] No hardcoded hex colours or URLs in the new templates or CSS
- [ ] `pytest` passes, including the new tests
- [ ] App starts on port 5001 with no errors and `/`, `/login`, `/register`, `/profile` still render
