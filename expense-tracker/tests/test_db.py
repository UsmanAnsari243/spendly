import sqlite3
from datetime import date

import pytest
from werkzeug.security import check_password_hash

from database import db


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    return db


def fetch_all(sql, params=()):
    conn = db.get_db()
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def test_init_db_is_idempotent_and_creates_tables(tmp_db):
    tmp_db.init_db()
    tables = {
        row["name"]
        for row in fetch_all("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    assert {"users", "expenses"} <= tables


def test_get_db_row_factory_and_foreign_keys(tmp_db):
    conn = tmp_db.get_db()
    try:
        assert conn.row_factory is sqlite3.Row
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    finally:
        conn.close()


def test_seed_creates_user_and_eight_expenses(tmp_db):
    tmp_db.seed_db()
    assert len(fetch_all("SELECT * FROM users")) == 1
    assert len(fetch_all("SELECT * FROM expenses")) == 8


def test_seed_covers_every_category(tmp_db):
    tmp_db.seed_db()
    used = {row["category"] for row in fetch_all("SELECT category FROM expenses")}
    assert used == set(tmp_db.CATEGORIES)


def test_seed_dates_are_in_current_month(tmp_db):
    tmp_db.seed_db()
    prefix = date.today().strftime("%Y-%m")
    dates = [row["date"] for row in fetch_all("SELECT date FROM expenses")]
    assert all(d.startswith(prefix) and len(d) == 10 for d in dates)


def test_seed_password_is_hashed(tmp_db):
    tmp_db.seed_db()
    user = fetch_all("SELECT * FROM users")[0]
    assert user["email"] == "demo@spendly.com"
    assert user["password_hash"] != "demo123"
    assert check_password_hash(user["password_hash"], "demo123")


def test_seed_twice_does_not_duplicate(tmp_db):
    tmp_db.seed_db()
    tmp_db.seed_db()
    assert len(fetch_all("SELECT * FROM users")) == 1
    assert len(fetch_all("SELECT * FROM expenses")) == 8


def test_duplicate_email_raises(tmp_db):
    conn = tmp_db.get_db()
    try:
        sql = "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)"
        conn.execute(sql, ("A", "a@x.com", "h"))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(sql, ("B", "a@x.com", "h"))
    finally:
        conn.close()


def test_expense_with_invalid_user_raises(tmp_db):
    conn = tmp_db.get_db()
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO expenses (user_id, amount, category, date) "
                "VALUES (?, ?, ?, ?)",
                (999, 10.0, "Food", "2026-01-01"),
            )
    finally:
        conn.close()
