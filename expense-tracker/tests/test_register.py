import sqlite3

import pytest
from werkzeug.security import check_password_hash

from database import db


def post_register(client, name="Test User", email="test@example.com", password="password123"):
    data = {}
    if name is not None:
        data["name"] = name
    if email is not None:
        data["email"] = email
    if password is not None:
        data["password"] = password
    return client.post("/register", data=data)


def fetch_users():
    conn = db.get_db()
    try:
        return conn.execute("SELECT * FROM users ORDER BY id").fetchall()
    finally:
        conn.close()


def test_get_register_renders_form(client):
    response = client.get("/register")
    assert response.status_code == 200
    assert b'action="/register"' in response.data
    assert b'minlength="8"' in response.data


def test_valid_registration_redirects_and_stores_user(client):
    before = len(fetch_users())
    response = post_register(client, name="  Ali Khan ", email="  New@Example.COM ")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")

    users = fetch_users()
    assert len(users) == before + 1
    user = users[-1]
    assert user["name"] == "Ali Khan"
    assert user["email"] == "new@example.com"
    assert user["password_hash"] != "password123"
    assert check_password_hash(user["password_hash"], "password123")

    conn = db.get_db()
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM expenses WHERE user_id = ?", (user["id"],)
        ).fetchone()[0]
    finally:
        conn.close()
    assert count == 0


@pytest.mark.parametrize("name", ["", "   "])
def test_blank_name_rejected(client, name):
    before = len(fetch_users())
    response = post_register(client, name=name)
    assert response.status_code == 400
    assert b"Name is required" in response.data
    assert len(fetch_users()) == before


@pytest.mark.parametrize("email", ["", "abc", "@x.com", "a@"])
def test_invalid_email_rejected(client, email):
    before = len(fetch_users())
    response = post_register(client, email=email)
    assert response.status_code == 400
    assert b"valid email" in response.data
    assert len(fetch_users()) == before


def test_short_password_rejected_and_eight_chars_accepted(client):
    before = len(fetch_users())
    response = post_register(client, password="1234567")
    assert response.status_code == 400
    assert len(fetch_users()) == before

    response = post_register(client, password="12345678")
    assert response.status_code == 302
    assert len(fetch_users()) == before + 1


@pytest.mark.parametrize("email", ["demo@spendly.com", "DEMO@Spendly.com"])
def test_duplicate_email_rejected(client, email):
    before = len(fetch_users())
    response = post_register(client, email=email)
    assert response.status_code == 400
    assert b"already exists" in response.data
    assert len(fetch_users()) == before


def test_failed_submit_prefills_name_and_email_but_not_password(client):
    response = post_register(client, name="Sara", email="sara@example.com", password="short")
    assert response.status_code == 400
    assert b'value="Sara"' in response.data
    assert b'value="sara@example.com"' in response.data
    assert b'value="short"' not in response.data


def test_missing_fields_return_400_not_500(client):
    response = client.post("/register", data={})
    assert response.status_code == 400


def test_name_is_html_escaped(client):
    response = post_register(client, name="<script>x</script>", email="bad")
    assert response.status_code == 400
    assert b"<script>x</script>" not in response.data
    assert b"&lt;script&gt;" in response.data


@pytest.mark.parametrize("path", ["/", "/login", "/terms", "/privacy"])
def test_other_pages_still_render(client, path):
    assert client.get(path).status_code == 200


def test_create_user_duplicate_raises_integrity_error(client):
    with pytest.raises(sqlite3.IntegrityError):
        db.create_user("Dup", "demo@spendly.com", "password123")
