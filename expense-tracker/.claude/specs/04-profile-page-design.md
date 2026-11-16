# Spec: Profile Page Design

## Overview

Replace the `/profile` placeholder string with a real, designed profile page. A logged-in user sees who they are (name, email, member-since date), a summary of their spending (total spent, number of expenses, top category, this-month total), a per-category breakdown, and a list of their most recent expenses. All amounts are shown in PKR. This is the first page that reads a user's own data, so it proves the users/expenses schema works end to end and gives later steps (add/edit/delete expenses) a place to land.

## Depends on

- Step 01 — Database setup (`users` and `expenses` tables, `get_db()`).
- Step 02 — Registration (users can exist beyond the seeded demo user).
- Step 03 — Login and logout. **Not yet implemented** (`/login` is GET-only, `/logout` is a stub, there is no `secret_key` or session). This spec requires `session["user_id"]` to be set by Step 03. Do not implement `/profile` until Step 03 is complete.

## Routes

- GET /profile — render the profile page for the current user; redirect to `/login` if not logged in; `abort(404)` if the session user no longer exists in the database — logged-in

(`/profile` already exists as a stub in `app.py`; it is replaced, not duplicated.)

## Database changes

No database changes. The existing `users` (`id`, `name`, `email`, `password_hash`, `created_at`) and `expenses` (`id`, `user_id`, `amount`, `category`, `date`, `description`, `created_at`) tables are sufficient.

Add these read-only helpers to `database/db.py` (parameterised queries, always close the connection, never return `password_hash`):

- `get_user_by_id(user_id)` — returns `id`, `name`, `email`, `created_at` for the user, or `None`.
- `get_expense_summary(user_id)` — returns total spent, expense count, and the current-month total (`date` starts with `YYYY-MM`, computed with a `?` parameter). Returns zeros when the user has no expenses.
- `get_category_breakdown(user_id)` — returns `(category, total, count)` rows ordered by total descending; empty list when no expenses. The top category is the first row.
- `get_recent_expenses(user_id, limit=5)` — returns the newest expenses (`ORDER BY date DESC, id DESC`) with `id`, `amount`, `category`, `date`, `description`.

Every query filters on `user_id = ?` so a user can only ever see their own data.

## Templates

- Create:
  - `templates/profile.html` — extends `base.html`; sections: profile header, summary stat cards, category breakdown, recent expenses.
- Modify:
  - `templates/base.html` — when logged in, show "Profile" and "Sign out" links (via `url_for('profile')` / `url_for('logout')`) in place of "Sign in" / "Get started". This depends on a session flag being available in templates (provided by Step 03).

### Page design

- **Header**: circular avatar showing the user's initials, name in `--font-display`, email, and "Member since <Month YYYY>".
- **Stat cards** (4 in a responsive grid): Total spent, This month, Expenses (count), Top category. Amounts formatted as `PKR 12,345` with thousands separators and no paise unless non-zero.
- **Category breakdown**: one row per category with name, amount, share of total as a percentage, and a horizontal bar whose width equals that percentage (set via a CSS custom property / `style="--pct: 42"`, not a hardcoded colour).
- **Recent expenses**: table or list of the last 5 expenses (date, description, category, amount). Description falls back to the category when blank.
- **Empty state**: a user with no expenses sees zeroed stat cards, a short "No expenses yet" message in place of the breakdown and list, and a link to `url_for('add_expense')`.
- **Responsive**: stat cards go 4 → 2 → 1 columns; the page works at 360px width without horizontal scroll.

## Files to change

- `app.py` — implement `profile()`: read `session["user_id"]`, call the db helpers, render `profile.html`; import the new helpers
- `database/db.py` — add the four helpers above
- `templates/base.html` — logged-in nav links
- `static/css/style.css` — only if a shared token is genuinely missing (prefer none)

## Files to create

- `templates/profile.html`
- `static/css/profile.css` — page-specific styles, linked from `profile.html` through `{% block head %}`
- `tests/test_profile.py` — redirect when logged out, 404 for missing user, correct totals for the demo user, empty state for a new user, and one user never seeing another's expenses

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug; `password_hash` must never be selected for or passed to the template
- Use CSS variables — never hardcode hex values (use `--accent`, `--accent-light`, `--paper-card`, `--border`, `--ink-muted`, etc. from `style.css`)
- All templates extend base.html
- DB logic lives in `database/db.py` only; the route fetches data, renders, and returns
- Use `url_for()` for every link and redirect
- Currency is PKR everywhere (label `PKR`, never `₹`, `Rs.` or `$`)
- Page-specific styles go in `static/css/profile.css`, not an inline `<style>` tag
- Use `abort()` for HTTP errors, not bare strings
- Vanilla JS only; this page needs no JS
- Do not add expense create/edit/delete behaviour here (Steps 7–9); links to those routes may exist but must not be expanded
- Do not change the port (5001)

## Definition of done

- [ ] Visiting `/profile` while logged out redirects (302) to `/login`
- [ ] Logged in as `demo@spendly.com`, `/profile` returns 200 and shows "Demo User" and the email, with no hash visible in the page source
- [ ] Total spent for the demo user shows `PKR 15,250` (sum of the 8 seeded expenses) and the expense count shows 8
- [ ] Top category is "Bills" (PKR 5,500) and the breakdown percentages add up to 100%
- [ ] Recent expenses lists exactly 5 rows, newest first
- [ ] A freshly registered user sees zeroed stat cards and the "No expenses yet" empty state with a working add-expense link
- [ ] A session pointing at a deleted user returns 404, not a 500
- [ ] User A can never see User B's expenses (verified with two users)
- [ ] The nav shows Profile / Sign out when logged in and Sign in / Get started when logged out
- [ ] Layout is usable at 360px and at 1280px with no horizontal scroll
- [ ] No hardcoded hex colours and no hardcoded URLs in the new template or CSS
- [ ] App starts on port 5001 with no errors and `/`, `/login`, `/register`, `/terms`, `/privacy` still render
