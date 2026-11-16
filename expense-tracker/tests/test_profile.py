import re
from datetime import date, timedelta

import pytest

from database import db

from conftest import login, set_session_user


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


def register(client, name, email):
    client.post(
        "/register",
        data={"name": name, "email": email, "password": "password123"},
    )
    return db.get_user_by_email(email)["id"]


# ----------------------------------------------------------------- access

def test_logged_out_redirects_to_login(client):
    response = client.get("/profile")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_session_for_missing_user_returns_404(client):
    set_session_user(client, 9999)
    assert client.get("/profile").status_code == 404


# ------------------------------------------------------------ demo content

def test_demo_profile_shows_identity_and_no_hash(client):
    login(client)
    response = client.get("/profile")
    assert response.status_code == 200
    assert b"Demo User" in response.data
    assert b"demo@spendly.com" in response.data
    assert b"Member since" in response.data

    password_hash = db.get_user_by_email("demo@spendly.com")["password_hash"]
    assert password_hash.encode() not in response.data


def test_demo_totals_and_top_category(client):
    login(client)
    html = client.get("/profile").get_data(as_text=True)

    assert "PKR 15,250" in html
    # this month == total because every seeded date is in the current month
    assert html.count("PKR 15,250") >= 2
    assert "PKR 5,500" in html

    top_card = re.search(
        r"Top category</span>\s*<span class=\"stat-value\">([^<]+)</span>", html
    )
    assert top_card and top_card.group(1).strip() == "Bills"
    assert re.search(r"Expenses</span>\s*<span class=\"stat-value\">8</span>", html)


def test_category_percentages_sum_to_100(client):
    login(client)
    html = client.get("/profile").get_data(as_text=True)
    percentages = [int(p) for p in re.findall(r'class="cat-pct">(\d+)%', html)]
    assert percentages
    assert sum(percentages) == 100


def test_recent_lists_five_newest_first(client):
    login(client)
    html = client.get("/profile").get_data(as_text=True)
    dates = re.findall(r'class="recent-sub">(\d{4}-\d{2}-\d{2}) ·', html)
    assert len(dates) == 5
    assert dates == sorted(dates, reverse=True)


def test_blank_description_falls_back_to_category(client):
    user_id = register(client, "Sara Malik", "sara@example.com")
    add_expense_row(user_id, 250.0, "Transport", date.today().isoformat(), "   ")
    login(client, "sara@example.com", "password123")
    html = client.get("/profile").get_data(as_text=True)
    assert re.search(r'class="recent-desc">Transport</span>', html)


# ------------------------------------------------------------- empty state

def test_new_user_sees_empty_state(client):
    register(client, "Ali Khan", "ali@example.com")
    login(client, "ali@example.com", "password123")
    response = client.get("/profile")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "No expenses yet" in html
    assert 'href="/expenses/add"' in html
    assert "PKR 0" in html
    assert re.search(r"Top category</span>\s*<span class=\"stat-value\">—</span>", html)


# --------------------------------------------------------------- isolation

def test_users_never_see_each_others_expenses(client):
    other_id = register(client, "Bilal Ahmed", "bilal@example.com")
    add_expense_row(other_id, 777.0, "Other", date.today().isoformat(), "Bilal secret lunch")

    login(client)
    demo_html = client.get("/profile").get_data(as_text=True)
    assert "Bilal secret lunch" not in demo_html

    client.get("/logout")
    login(client, "bilal@example.com", "password123")
    bilal_html = client.get("/profile").get_data(as_text=True)
    assert "Bilal secret lunch" in bilal_html
    assert "Groceries" not in bilal_html


# --------------------------------------------------------------------- nav

def test_nav_reflects_login_state(client):
    logged_out = client.get("/").get_data(as_text=True)
    assert "Sign in" in logged_out and "Get started" in logged_out
    assert "Sign out" not in logged_out

    login(client)
    logged_in = client.get("/profile").get_data(as_text=True)
    assert "Sign out" in logged_in
    assert "Get started" not in logged_in


# ------------------------------------------------------------ db helpers

def test_summary_for_user_without_expenses_is_zero(client):
    user_id = register(client, "Zara Noor", "zara@example.com")
    assert db.get_expense_summary(user_id) == {"total": 0, "count": 0, "month_total": 0}
    assert list(db.get_category_breakdown(user_id)) == []
    assert list(db.get_recent_expenses(user_id)) == []


def test_unknown_user_id_returns_none(client):
    assert db.get_user_by_id(424242) is None
    assert db.get_user_by_email("nobody@example.com") is None


def test_get_user_by_id_never_returns_password_hash(client):
    assert "password_hash" not in db.get_user_by_id(demo_id()).keys()


def test_recent_expenses_respects_limit(client):
    assert len(db.get_recent_expenses(demo_id(), limit=3)) == 3


def test_last_month_counts_in_total_but_not_this_month(client):
    user_id = register(client, "Hina Raza", "hina@example.com")
    last_month = (date.today().replace(day=1) - timedelta(days=1)).isoformat()
    add_expense_row(user_id, 1000.0, "Food", last_month, "Old")
    add_expense_row(user_id, 500.0, "Food", date.today().isoformat(), "New")

    summary = db.get_expense_summary(user_id)
    assert summary["total"] == 1500
    assert summary["month_total"] == 500
    assert summary["count"] == 2


# ----------------------------------------------------- presentation helpers

@pytest.mark.parametrize(
    "amount, expected",
    [
        (1200.0, "PKR 1,200"),
        (1200.5, "PKR 1,200.50"),
        (0, "PKR 0"),
        (None, "PKR 0"),
        (15250, "PKR 15,250"),
    ],
)
def test_pkr_filter(client, amount, expected):
    import app as app_module

    assert app_module.format_pkr(amount) == expected


def test_round_percentages_sum_to_100_and_handle_empty(client):
    import app as app_module

    assert sum(app_module.round_percentages([1, 1, 1])) == 100
    assert sum(app_module.round_percentages([5500, 3200, 2000, 1500, 1200, 850, 400, 600])) == 100
    assert app_module.round_percentages([]) == []
    assert app_module.round_percentages([0, 0]) == [0, 0]


@pytest.mark.parametrize(
    "name, expected",
    [("Ali Khan", "AK"), ("sara", "S"), ("  ", "?"), ("a b c", "AB")],
)
def test_build_initials(client, name, expected):
    import app as app_module

    assert app_module.build_initials(name) == expected
