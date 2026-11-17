import re
from pathlib import Path

import pytest
from conftest import login, set_session_user

from database import db

ROOT = Path(__file__).resolve().parent.parent


def demo_id():
    return db.get_user_by_email("demo@spendly.com")["id"]


def add_expense_row(user_id, amount, category, day, description):
    conn = db.get_db()
    try:
        with conn:
            conn.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, amount, category, day, description),
            )
    finally:
        conn.close()


def page(client, path="/profile"):
    return client.get(path).data.decode()


# ---- access ---------------------------------------------------------------

def test_logged_out_redirects_to_login(client):
    response = client.get("/profile")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_deleted_user_session_returns_404(client):
    set_session_user(client, 9999)
    assert client.get("/profile").status_code == 404


# ---- demo user content ----------------------------------------------------

def test_demo_profile_shows_identity_without_hash(client):
    login(client)
    response = client.get("/profile")
    html = response.data.decode()
    assert response.status_code == 200
    assert "Demo User" in html and "demo@spendly.com" in html
    password_hash = db.get_user_by_email("demo@spendly.com")["password_hash"]
    assert password_hash not in html
    assert "scrypt:" not in html and "pbkdf2:" not in html


def test_demo_totals_and_count(client):
    login(client)
    html = page(client)
    assert "PKR 15,250" in html
    assert re.search(r'stat-value">\s*8\s*<', html)


def test_top_category_and_percentages_sum_to_100(client):
    login(client)
    html = page(client)
    assert "Bills" in html and "PKR 5,500" in html
    pcts = [int(p) for p in re.findall(r"--pct:\s*(\d+)", html)]
    assert pcts == [36, 21, 13, 13, 10, 4, 3]
    assert sum(pcts) == 100


def test_recent_lists_five_newest_first(client):
    login(client)
    html = page(client)
    assert html.count('class="recent-row"') == 5
    order = ["Dinner out", "Miscellaneous", "New shoes", "Cinema tickets", "Pharmacy"]
    positions = [html.index(name) for name in order]
    assert positions == sorted(positions)
    assert "Groceries" not in html


# ---- empty state and isolation -------------------------------------------

def test_new_user_sees_empty_state(client):
    client.post(
        "/register",
        data={"name": "Fresh User", "email": "fresh@example.com", "password": "password123"},
    )
    login(client, email="fresh@example.com", password="password123")
    html = page(client)
    assert "No expenses yet" in html
    assert "PKR 0" in html
    assert 'href="/expenses/add"' in html
    assert "--pct" not in html
    assert client.get("/expenses/add").status_code == 200


def test_users_never_see_each_others_expenses(client):
    other_id = db.create_user("Other Person", "other@example.com", "password123")
    add_expense_row(other_id, 777.0, "Other", "2026-01-05", "SECRET-B-ITEM")

    login(client)
    html = page(client)
    assert "SECRET-B-ITEM" not in html
    assert "PKR 15,250" in html

    other = client.application.test_client()
    login(other, email="other@example.com", password="password123")
    html = other.get("/profile").data.decode()
    assert "SECRET-B-ITEM" in html and "PKR 777" in html
    assert "Electricity bill" not in html


def test_nav_toggles_with_session(client):
    html = page(client, "/")
    assert "Sign in" in html and "Get started" in html
    login(client)
    html = page(client)
    assert "Sign out" in html and "Get started" not in html


# ---- db helpers -----------------------------------------------------------

def test_db_helpers_scope_and_zeros(client):
    new_id = db.create_user("Empty User", "empty@example.com", "password123")
    assert db.get_expense_summary(new_id) == {"total": 0, "count": 0, "month_total": 0}
    assert db.get_category_breakdown(new_id) == []
    assert db.get_recent_expenses(new_id) == []

    user = db.get_user_by_id(demo_id())
    assert "password_hash" not in user.keys()
    assert db.get_user_by_id(9999) is None

    assert db.get_expense_summary(demo_id(), month="1999-01")["month_total"] == 0
    assert len(db.get_recent_expenses(demo_id(), limit=3)) == 3


# ---- presentation helpers -------------------------------------------------

def test_pkr_filter_and_percentages_helper(client):
    import app as app_module

    assert app_module.format_pkr(15250) == "PKR 15,250"
    assert app_module.format_pkr(99.5) == "PKR 99.50"
    assert app_module.format_pkr(0) == "PKR 0"
    assert app_module.format_pkr(None) == "PKR 0"

    thirds = [{"category": c, "total": 10, "count": 1} for c in "abc"]
    result = app_module.with_percentages(thirds, 30)
    assert sorted(r["pct"] for r in result) == [33, 33, 34]
    assert sum(r["pct"] for r in result) == 100
    assert app_module.with_percentages([], 0) == []

    assert app_module.initials("Demo User") == "DU"
    assert app_module.initials("  ") == "?"
    assert app_module.member_since("2026-11-15 10:20:02") == "November 2026"


# ---- period filter --------------------------------------------------------

def test_period_form_shown_without_dates(client):
    login(client)
    html = page(client)
    assert "Expenses by period" in html
    assert 'name="from"' in html and 'name="to"' in html
    assert "Pick a start and end date" in html


def test_period_lists_only_expenses_in_range(client):
    uid = demo_id()
    add_expense_row(uid, 111.0, "Food", "2025-03-10", "OLD-MARCH-A")
    add_expense_row(uid, 222.0, "Bills", "2025-03-20", "OLD-MARCH-B")
    add_expense_row(uid, 333.0, "Other", "2025-04-02", "OLD-APRIL")
    login(client)
    html = page(client, "/profile?from=2025-03-01&to=2025-03-31")
    assert "OLD-MARCH-A" in html and "OLD-MARCH-B" in html
    assert "OLD-APRIL" not in html
    assert "2 expenses" in html and "PKR 333" in html


def test_period_range_is_inclusive_and_empty_message(client):
    uid = demo_id()
    add_expense_row(uid, 50.0, "Food", "2025-05-01", "EDGE-START")
    add_expense_row(uid, 60.0, "Food", "2025-05-31", "EDGE-END")
    login(client)
    html = page(client, "/profile?from=2025-05-01&to=2025-05-31")
    assert "EDGE-START" in html and "EDGE-END" in html
    empty = page(client, "/profile?from=1999-01-01&to=1999-01-31")
    assert "No expenses between 1999-01-01 and 1999-01-31." in empty


def test_period_updates_stat_cards(client):
    uid = demo_id()
    add_expense_row(uid, 1000.0, "Shopping", "2025-03-10", "S-A")
    add_expense_row(uid, 500.0, "Food", "2025-03-20", "S-B")
    add_expense_row(uid, 700.0, "Food", "2025-02-05", "S-C")
    login(client)
    html = page(client, "/profile?from=2025-03-01&to=2025-03-31")
    cards = html.split('aria-label="Spending summary"')[1].split("</section>")[0]
    assert "PKR 1,500" in cards          # total spent in range
    assert "March 2025" in cards         # month card follows the range end
    assert "Shopping" in cards           # top category within range
    assert "PKR 15,250" not in cards     # all-time total no longer shown


def test_summary_and_breakdown_helpers_respect_range(client):
    uid = demo_id()
    add_expense_row(uid, 40.0, "Food", "2025-06-01", "H-A")
    add_expense_row(uid, 60.0, "Bills", "2025-07-01", "H-B")
    summary = db.get_expense_summary(uid, "2025-06", "2025-06-01", "2025-06-30")
    assert summary == {"total": 40.0, "count": 1, "month_total": 40.0}
    rows = db.get_category_breakdown(uid, "2025-06-01", "2025-06-30")
    assert [(r["category"], r["total"]) for r in rows] == [("Food", 40.0)]


@pytest.mark.parametrize(
    "query, message",
    [
        ("from=2025-05-31&to=2025-05-01", "start date must be on or before"),
        ("from=2025-05-01", "both a start and an end date"),
        ("from=not-a-date&to=2025-05-01", "valid dates"),
    ],
)
def test_period_invalid_input_shows_error_not_500(client, query, message):
    login(client)
    response = client.get("/profile?" + query)
    assert response.status_code == 200
    assert message in response.data.decode()


def test_period_never_shows_other_users_expenses(client):
    other_id = db.create_user("Other Person", "other@example.com", "password123")
    add_expense_row(other_id, 999.0, "Other", "2025-06-15", "OTHER-USER-PERIOD")
    login(client)
    html = page(client, "/profile?from=2025-06-01&to=2025-06-30")
    assert "OTHER-USER-PERIOD" not in html


def test_period_requires_login(client):
    response = client.get("/profile?from=2025-01-01&to=2025-01-31")
    assert response.status_code == 302


def test_get_expenses_between_helper(client):
    uid = demo_id()
    add_expense_row(uid, 10.0, "Food", "2025-07-01", "H1")
    add_expense_row(uid, 20.0, "Food", "2025-07-02", "H2")
    rows = db.get_expenses_between(uid, "2025-07-01", "2025-07-02")
    assert [r["description"] for r in rows] == ["H2", "H1"]
    assert db.get_expenses_between(uid, "2025-08-01", "2025-08-31") == []


# ---- project rules --------------------------------------------------------

def test_no_hex_or_hardcoded_urls_in_new_files():
    css = (ROOT / "static" / "css" / "profile.css").read_text(encoding="utf-8")
    template = (ROOT / "templates" / "profile.html").read_text(encoding="utf-8")
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", css)
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", template)
    assert 'href="/' not in template and 'src="/' not in template


@pytest.mark.parametrize("path", ["/", "/login", "/register", "/terms", "/privacy"])
def test_public_pages_still_render(client, path):
    assert client.get(path).status_code == 200
