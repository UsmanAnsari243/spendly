"""Tests for Step 7: adding an expense."""

import sqlite3
from datetime import date, timedelta

import pytest

from conftest import login, set_session_user
from database import db

TODAY = date.today().isoformat()


def valid_data(**overrides):
    data = {
        "amount": "123.45",
        "category": db.CATEGORIES[0],
        "date": TODAY,
        "description": "Lunch",
    }
    data.update(overrides)
    return data


def all_expenses():
    conn = sqlite3.connect(db.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute("SELECT * FROM expenses ORDER BY id").fetchall()
    finally:
        conn.close()


def post_add(client, **overrides):
    return client.post("/expenses/add", data=valid_data(**overrides))


def test_logged_out_get_redirects_to_login(client):
    response = client.get("/expenses/add")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_logged_out_post_redirects_and_inserts_nothing(client):
    before = len(all_expenses())
    response = post_add(client)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    assert len(all_expenses()) == before


def test_session_for_missing_user_is_404(client):
    set_session_user(client, 9999)
    assert client.get("/expenses/add").status_code == 404


def test_get_renders_form(client):
    login(client)
    response = client.get("/expenses/add")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Amount (PKR)" in html
    assert f'max="{TODAY}"' in html
    assert f'value="{TODAY}"' in html
    assert 'maxlength="200"' in html


def test_category_dropdown_lists_exactly_the_categories(client):
    login(client)
    html = client.get("/expenses/add").get_data(as_text=True)
    for category in db.CATEGORIES:
        assert f'<option value="{category}"' in html
    # Every real option has a value; the placeholder's value is empty.
    assert html.count("<option value=") - 1 == len(db.CATEGORIES)


def test_nav_link_only_when_logged_in(client):
    assert "/expenses/add" not in client.get("/").get_data(as_text=True)
    login(client)
    assert "/expenses/add" in client.get("/profile").get_data(as_text=True)


def test_valid_post_inserts_and_redirects_to_profile(client):
    login(client)
    before = len(all_expenses())
    response = post_add(client, description="Zebra snacks")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")

    rows = all_expenses()
    assert len(rows) == before + 1
    row = rows[-1]
    assert row["user_id"] == 1
    assert row["amount"] == pytest.approx(123.45)
    assert row["category"] == db.CATEGORIES[0]
    assert row["date"] == TODAY
    assert row["description"] == "Zebra snacks"

    profile = client.get("/profile").get_data(as_text=True)
    assert "Zebra snacks" in profile


def test_total_increases_after_adding(client):
    login(client)
    before = db.get_expense_summary(1)["total"]
    post_add(client, amount="500")
    assert db.get_expense_summary(1)["total"] == pytest.approx(before + 500)


@pytest.mark.parametrize("description", ["", "   "])
def test_blank_description_is_stored_as_null(client, description):
    login(client)
    post_add(client, description=description)
    assert all_expenses()[-1]["description"] is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"description": "x" * 200},
        {"amount": "0.01"},
        {"amount": "100"},
        {"amount": "99.9"},
        {"amount": "10000000"},
    ],
)
def test_boundary_values_are_accepted(client, overrides):
    login(client)
    before = len(all_expenses())
    assert post_add(client, **overrides).status_code == 302
    assert len(all_expenses()) == before + 1


def test_form_supplied_user_id_is_ignored(client):
    other_id = db.create_user("Other Person", "other@spendly.com", "password123")
    login(client)
    client.post("/expenses/add", data=valid_data(user_id=str(other_id)))
    assert all_expenses()[-1]["user_id"] == 1


INVALID_FORMS = [
    ({"amount": ""}, "Amount is required"),
    ({"amount": "   "}, "Amount is required"),
    ({"amount": "abc"}, "valid amount"),
    ({"amount": "nan"}, "valid amount"),
    ({"amount": "inf"}, "valid amount"),
    ({"amount": "-inf"}, "valid amount"),
    ({"amount": "1_000"}, "valid amount"),
    ({"amount": "0"}, "greater than 0"),
    ({"amount": "-5"}, "greater than 0"),
    ({"amount": "1.234"}, "2 decimal places"),
    ({"amount": "10000000.01"}, "at most PKR"),
    ({"amount": "99999999999"}, "at most PKR"),
    ({"category": "Bogus"}, "valid category"),
    ({"category": ""}, "valid category"),
    ({"category": "food"}, "valid category"),
    ({"date": ""}, "valid date"),
    ({"date": "not-a-date"}, "valid date"),
    ({"date": "2026-13-40"}, "valid date"),
    ({"date": "20260101"}, "valid date"),
    ({"date": (date.today() + timedelta(days=1)).isoformat()}, "in the future"),
    ({"description": "x" * 201}, "200 characters"),
]


@pytest.mark.parametrize("overrides,message", INVALID_FORMS)
def test_invalid_input_returns_400_and_inserts_nothing(client, overrides, message):
    login(client)
    before = len(all_expenses())
    response = post_add(client, **overrides)
    assert response.status_code == 400
    assert message in response.get_data(as_text=True)
    assert len(all_expenses()) == before


def test_failed_post_echoes_submitted_values(client):
    login(client)
    category = db.CATEGORIES[2]
    response = post_add(
        client,
        amount="1.234",
        category=category,
        date="2026-01-15",
        description="Keep me",
    )
    html = response.get_data(as_text=True)
    assert response.status_code == 400
    assert 'value="1.234"' in html
    assert f'<option value="{category}" selected>' in html
    assert 'value="2026-01-15"' in html
    assert 'value="Keep me"' in html


def test_expenses_are_isolated_per_user(client):
    db.create_user("Other Person", "other@spendly.com", "password123")
    demo_before = len(db.get_recent_expenses(1, limit=100))

    login(client, "other@spendly.com", "password123")
    post_add(client, description="Other users secret lunch")

    other_page = client.get("/profile").get_data(as_text=True)
    assert "Other users secret lunch" in other_page

    client.get("/logout")
    login(client)
    demo_page = client.get("/profile").get_data(as_text=True)
    assert "Other users secret lunch" not in demo_page
    assert len(db.get_recent_expenses(1, limit=100)) == demo_before


def test_create_expense_helper_returns_id_and_stores_null_description(client):
    expense_id = db.create_expense(1, 42.5, "Food", TODAY)
    assert isinstance(expense_id, int)
    row = all_expenses()[-1]
    assert row["id"] == expense_id
    assert row["description"] is None


def test_edit_and_delete_stubs_still_respond(client):
    assert client.get("/expenses/1/edit").status_code == 200
    assert client.get("/expenses/1/delete").status_code == 200
