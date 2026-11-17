---
name: expense-tracker-patterns
description: "Use when working in the Spendly expense-tracker repo, especially before starting a numbered feature step, adding a route/page/DB helper, placing tests, naming a branch, or writing a commit — conventions measured from git history"
metadata:
  version: "1.0.0"
  source: local-git-analysis
  analyzed_commits: "10"
---

# Expense Tracker (Spendly) Patterns

Measured from 10 commits (8 non-merge, 2 PR merges), 2026-11-09 → 2026-11-15.
CLAUDE.md holds the hard rules (Flask/SQLite/vanilla JS, url_for, parameterised SQL);
this skill covers the *workflow* conventions observed in history.

## Commit Conventions

- Free-form, sentence-case summaries — **not** Conventional Commits
  (only 1 of 8 used a prefix: `landing: add terms and conditions page route`).
- Typical forms: `Implement SQLite database setup with seed data`,
  `Add project CLAUDE.md and Claude tooling config`.
- Prefer the clearer imperative style: `Implement <feature>` / `Add <thing>`.
- One commit per feature step is the norm; features land on `main` via a GitHub PR merge
  (`Merge pull request #N from <owner>/feature/<slug>`).

## Branching

- Feature branches: `feature/<kebab-slug>` matching the spec slug
  (`feature/database-setup`, `feature/registration`).
- Branch from an up-to-date `main`; merge back through a PR, not a local merge.

## Code Architecture

- Git root is `D:\expense-tracker`; the app lives in nested `expense-tracker/` — run
  `python app.py` / `pytest` from there. Ignore `__MACOSX/` and `venv/`.
- `app.py` — every route (no blueprints) plus small presentation helpers
  (`format_pkr`, `build_initials`, `format_member_since`, `round_percentages`).
- `database/db.py` — all SQL: `get_db`, `init_db`, `seed_db`, then feature helpers
  (`create_user`, `get_user_by_email`, `get_user_by_id`, `get_expense_summary`,
  `get_category_breakdown`, `get_recent_expenses`). Helpers open and close their own connection.
- `templates/<page>.html` — one per page, extends `base.html`.
- `static/css/<page>.css` — page-specific stylesheet (e.g. `profile.css`); global in `style.css`.
- Localisation: money is PKR (`format_pkr`), sample names/places are Pakistani (e.g. "Ali Khan").

## Workflows

### Numbered spec-driven feature step
1. Write `expense-tracker/.claude/specs/NN-<slug>.md` (two-digit step number, kebab slug —
   e.g. `01-database-setup.md`, `02-registration.md`). Use `/create-spec`.
   Sections: Overview, Depends on, Routes, Database changes, Templates, Files to change,
   Files to create, New dependencies, Rules for implementation, Definition of done.
2. Optional plan in `.claude/plans/NN-<slug>.md`.
3. Branch `feature/<slug>`.
4. Implement — files that change together in every feature commit:
   - `database/db.py` (new helper) + `app.py` (route calls helper)
   - `templates/<page>.html` (+ `base.html` if nav/footer links change)
   - `tests/test_<slug>.py`
5. Commit spec + code + tests together, open a PR.

### Adding a static/legal page
`app.py` route + new `templates/<page>.html` + `static/css/style.css` + `base.html`
footer link (seen for `terms` and `privacy`).

### Tooling noise
`expense-tracker/.impeccable/hook.cache.json` is modified by design-tool hooks and shows
up in feature commits; it is not feature code — don't hand-edit it.

## Testing Patterns

- pytest + pytest-flask; files at `expense-tracker/tests/test_<feature>.py`
  (`test_db.py`, `test_register.py`, `test_login.py`, `test_profile.py`).
- `tests/conftest.py` provides:
  - `client` fixture — monkeypatches `db.DB_PATH` to `tmp_path/test.db` and
    `importlib.reload(app)` so `init_db()`/`seed_db()` rerun; the real `spendly.db` is never touched.
  - `login(client, ...)` — logs in as the seeded demo user.
  - `set_session_user(client, user_id)` — sets `session["user_id"]` directly.
- Module-local helpers per test file (e.g. `post_register(...)`, `fetch_users()` using
  `db.get_db()` with `try/finally: conn.close()`).
- Test names: `test_<behaviour_in_snake_case>`; assert status codes, redirect `Location`,
  and response bytes (`b'minlength="8"' in response.data`).
- Validation failures re-render the form with HTTP 400; success redirects with 302.
