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
