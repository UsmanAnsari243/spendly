import os
import sqlite3
from datetime import date

from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "spendly.db")

CATEGORIES = [
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at    TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS expenses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    amount      REAL NOT NULL,
    category    TEXT NOT NULL,
    date        TEXT NOT NULL,
    description TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);
"""


def get_db():
    """Return a new SQLite connection; the caller is responsible for closing it."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all tables if they do not exist yet. Safe to call repeatedly."""
    conn = get_db()
    try:
        conn.executescript(SCHEMA)
    finally:
        conn.close()


def seed_db():
    """Insert the demo user and sample expenses once; no-op if users exist."""
    conn = get_db()
    try:
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
            return

        today = date.today()

        def day_in_month(day):
            # Keep seeded dates inside the current month and never in the future.
            return date(today.year, today.month, min(day, today.day)).isoformat()

        with conn:
            cursor = conn.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                (
                    "Demo User",
                    "demo@spendly.com",
                    generate_password_hash("demo123"),
                ),
            )
            user_id = cursor.lastrowid

            expenses = [
                (user_id, 1200.0, "Food", day_in_month(2), "Groceries"),
                (user_id, 400.0, "Transport", day_in_month(4), "Bus and rickshaw fares"),
                (user_id, 5500.0, "Bills", day_in_month(6), "Electricity bill"),
                (user_id, 1500.0, "Health", day_in_month(9), "Pharmacy"),
                (user_id, 2000.0, "Entertainment", day_in_month(12), "Cinema tickets"),
                (user_id, 3200.0, "Shopping", day_in_month(15), "New shoes"),
                (user_id, 600.0, "Other", day_in_month(18), "Miscellaneous"),
                (user_id, 850.0, "Food", day_in_month(21), "Dinner out"),
            ]
            conn.executemany(
                "INSERT INTO expenses (user_id, amount, category, date, description) "
                "VALUES (?, ?, ?, ?, ?)",
                expenses,
            )
    finally:
        conn.close()


def create_user(name, email, password):
    """Insert a new user with a hashed password and return the new user id.

    A duplicate email raises sqlite3.IntegrityError (UNIQUE constraint).
    """
    conn = get_db()
    try:
        with conn:
            cursor = conn.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                (name, email, generate_password_hash(password)),
            )
            return cursor.lastrowid
    finally:
        conn.close()


def get_user_by_email(email):
    """Return the user row (including password_hash) for login, or None.

    For authentication only: never pass this row to a template.
    """
    conn = get_db()
    try:
        return conn.execute(
            "SELECT id, name, email, password_hash FROM users WHERE email = ?",
            (email,),
        ).fetchone()
    finally:
        conn.close()


def get_user_by_id(user_id):
    """Return id, name, email and created_at for a user (never the hash), or None."""
    conn = get_db()
    try:
        return conn.execute(
            "SELECT id, name, email, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()


def update_user(user_id, name, email):
    """Update a user's name and email; return True if a row was changed.

    A duplicate email raises sqlite3.IntegrityError (same contract as create_user).
    """
    conn = get_db()
    try:
        with conn:
            cursor = conn.execute(
                "UPDATE users SET name = ?, email = ? WHERE id = ?",
                (name, email, user_id),
            )
            return cursor.rowcount > 0
    finally:
        conn.close()


def get_password_hash(user_id):
    """Return the stored password hash for verification, or None.

    For use inside routes only: never pass this value to a template.
    """
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT password_hash FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        return row["password_hash"] if row else None
    finally:
        conn.close()


def update_password(user_id, new_password):
    """Hash and store a new password; return True if a row was changed."""
    conn = get_db()
    try:
        with conn:
            cursor = conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (generate_password_hash(new_password), user_id),
            )
            return cursor.rowcount > 0
    finally:
        conn.close()


def get_expense_summary(user_id, month=None, start=None, end=None):
    """Return {"total", "count", "month_total"} for a user; zeros when empty.

    `month` is "YYYY-MM" and defaults to the current month. `start`/`end`
    ("YYYY-MM-DD", inclusive) optionally limit every figure to that range.
    """
    if month is None:
        month = date.today().strftime("%Y-%m")
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total, "
            "COUNT(*) AS count, "
            "COALESCE(SUM(CASE WHEN substr(date, 1, 7) = ? THEN amount END), 0) "
            "AS month_total "
            "FROM expenses WHERE user_id = ? "
            "AND (? IS NULL OR date >= ?) AND (? IS NULL OR date <= ?)",
            (month, user_id, start, start, end, end),
        ).fetchone()
        return {
            "total": row["total"],
            "count": row["count"],
            "month_total": row["month_total"],
        }
    finally:
        conn.close()


def get_category_breakdown(user_id, start=None, end=None):
    """Return (category, total, count) rows, largest total first.

    `start`/`end` ("YYYY-MM-DD", inclusive) optionally limit the rows.
    """
    conn = get_db()
    try:
        return conn.execute(
            "SELECT category, SUM(amount) AS total, COUNT(*) AS count "
            "FROM expenses WHERE user_id = ? "
            "AND (? IS NULL OR date >= ?) AND (? IS NULL OR date <= ?) "
            "GROUP BY category ORDER BY total DESC, category ASC",
            (user_id, start, start, end, end),
        ).fetchall()
    finally:
        conn.close()


def get_expenses_between(user_id, start, end):
    """Return all of a user's expenses dated from `start` to `end` inclusive.

    `start` and `end` are "YYYY-MM-DD" strings; newest first.
    """
    conn = get_db()
    try:
        return conn.execute(
            "SELECT id, amount, category, date, description "
            "FROM expenses WHERE user_id = ? AND date >= ? AND date <= ? "
            "ORDER BY date DESC, id DESC",
            (user_id, start, end),
        ).fetchall()
    finally:
        conn.close()


def get_recent_expenses(user_id, limit=5):
    """Return the user's newest expenses."""
    conn = get_db()
    try:
        return conn.execute(
            "SELECT id, amount, category, date, description "
            "FROM expenses WHERE user_id = ? "
            "ORDER BY date DESC, id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    finally:
        conn.close()


def create_expense(user_id, amount, category, expense_date, description=None):
    """Insert one expense for a user and return the new expense id.

    `expense_date` is a "YYYY-MM-DD" string. Validation is the caller's job.
    """
    conn = get_db()
    try:
        with conn:
            cursor = conn.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, amount, category, expense_date, description),
            )
            return cursor.lastrowid
    finally:
        conn.close()
