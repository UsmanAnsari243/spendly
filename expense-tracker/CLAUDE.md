# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

"Spendly" — a Flask expense tracker built as a step-by-step teaching project. The git root is `D:\expense-tracker`; the app lives in the nested `expense-tracker/` directory (run everything from there). `venv/` and `__MACOSX/` at the git root are not part of the app.

## Architecture

spendly/
├── app.py              # All routes — single file, no blueprints
├── database/
│   └── db.py           # SQLite helpers: get_db(), init_db(), seed_db()
├── templates/
│   ├── base.html       # Shared layout — all templates must extend this
│   └── *.html          # One template per page
├── static/
│   ├── css/
│   │   ├── style.css       # Global styles
│   │   └── landing.css     # Landing-page-only styles
│   └── js/
│       └── main.js         # Vanilla JS only
└── requirements.txt

## Where things belong

New routes → app.py only, no blueprints
DB logic → database/db.py only, never inline in routes
New pages → new .html file extending base.html
Page-specific styles → new .css file, not inline <style> tags

## Code style

Python: PEP 8, snake_case for all variables and functions
Templates: Jinja2 with url_for() for every internal link — never hardcode URLs
Route functions: one responsibility only — fetch data, render template, done
DB queries: always use parameterized queries (? placeholders) — never f-strings in SQL
Error handling: use abort() for HTTP errors, not bare return "error string"

## Tech constraints

Flask only — no FastAPI, no Django, no other web frameworks
SQLite only — no PostgreSQL, no SQLAlchemy ORM, no external DB
Vanilla JS only — no React, no jQuery, no npm packages
No new pip packages — work within requirements.txt as-is unless explicitly told otherwise
Python 3.10+ assumed — f-strings and match statements are fine

## Subagent Policy

Always use a builtin explore subagent for codebase exploration before implementing any new feature
Always use a subagent to verify test results after any implementation
When asked to plan, delegate codebase research to a subagent before presenting the plan
always use a builtin plan subagent in plan mode

## Commands

```bash
pip install -r requirements.txt      # flask, werkzeug, pytest, pytest-flask
python app.py                        # dev server on http://localhost:5001 (debug=True)
pytest                               # run tests (no tests exist yet)
pytest path/to/test_file.py::test_name   # single test
```

No linter or build step is configured.

## Warnings and things to avoid

Never use raw string returns for stub routes once a step is implemented — always render a template
Never hardcode URLs in templates — always use url_for()
Never put DB logic in route functions — it belongs in database/db.py
Never install new packages mid-feature without flagging it — keep requirements.txt in sync
Never use JS frameworks — the frontend is intentionally vanilla
database/db.py is currently empty — do not assume helpers exist until the step that implements them
FK enforcement is manual — SQLite foreign keys are off by default; get_db() must run PRAGMA foreign_keys = ON on every connection
The app runs on port 5001, not the Flask default 5000 — don't change this