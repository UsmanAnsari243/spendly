"""Tests for Step 05: profile edit and change-password routes."""
import pytest
from werkzeug.security import check_password_hash

from conftest import login, set_session_user  # noqa: F401
from database import db

DEMO_EMAIL = "demo@spendly.com"
DEMO_PASSWORD = "demo123"
NEW_PASSWORD = "brandnew99"
LONG_PASSWORD = "longenough1"

ROUTES = ["/profile/edit", "/profile/password"]


def fetch_user(email=None, user_id=None):
    conn = db.get_db()
    try:
        if user_id is not None:
            return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    finally:
        conn.close()


def demo_user():
    return fetch_user(email=DEMO_EMAIL)


def post_edit(client, name="Demo User", email=DEMO_EMAIL, **extra):
    return client.post("/profile/edit", data={"name": name, "email": email, **extra})


def post_password(client, current=DEMO_PASSWORD, new=NEW_PASSWORD, confirm=None):
    return client.post(
        "/profile/password",
        data={
            "current_password": current,
            "new_password": new,
            "confirm_password": new if confirm is None else confirm,
        },
    )


# ---------------------------------------------------------------- auth ----

@pytest.mark.parametrize("path", ROUTES)
def test_logged_out_get_redirects_to_login(client, path):
    response = client.get(path)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


@pytest.mark.parametrize("path", ROUTES)
def test_logged_out_post_redirects_and_changes_nothing(client, path):
    before = demo_user()
    response = client.post(
        path,
        data={
            "name": "Hacker",
            "email": "hacker@example.com",
            "current_password": DEMO_PASSWORD,
            "new_password": NEW_PASSWORD,
            "confirm_password": NEW_PASSWORD,
        },
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    after = demo_user()
    assert after["name"] == before["name"]
    assert after["email"] == before["email"]
    assert after["password_hash"] == before["password_hash"]


@pytest.mark.parametrize("path", ROUTES)
def test_deleted_user_session_gets_404(client, path):
    set_session_user(client, 9999)
    assert client.get(path).status_code == 404
    assert client.post(path, data={"name": "x", "email": "x@example.com"}).status_code == 404


# ----------------------------------------------------------- edit profile ----

def test_edit_form_is_prefilled(client):
    login(client)
    response = client.get("/profile/edit")
    assert response.status_code == 200
    assert b'value="Demo User"' in response.data
    assert b'value="demo@spendly.com"' in response.data


def test_edit_success_updates_and_redirects(client):
    login(client)
    demo_id = demo_user()["id"]
    response = post_edit(client, name="Ayesha Malik", email="ayesha@example.com")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")

    user = fetch_user(user_id=demo_id)
    assert user["name"] == "Ayesha Malik"
    assert user["email"] == "ayesha@example.com"

    page = client.get("/profile")
    assert b"Ayesha Malik" in page.data
    assert b"ayesha@example.com" in page.data


def test_edit_normalises_email(client):
    login(client)
    post_edit(client, name="  Demo User  ", email="  New@Spendly.com ")
    user = fetch_user(email="new@spendly.com")
    assert user is not None
    assert user["name"] == "Demo User"


def test_edit_empty_name_returns_400(client):
    login(client)
    response = post_edit(client, name="   ", email="keep@example.com")
    assert response.status_code == 400
    assert b"Name is required." in response.data
    assert b'value="keep@example.com"' in response.data
    assert demo_user()["email"] == DEMO_EMAIL


@pytest.mark.parametrize("bad_email", ["nope", "@example.com", "user@"])
def test_edit_bad_email_returns_400(client, bad_email):
    login(client)
    response = post_edit(client, email=bad_email)
    assert response.status_code == 400
    assert b"Please enter a valid email address." in response.data
    assert demo_user()["email"] == DEMO_EMAIL


def test_edit_duplicate_email_returns_400(client):
    db.create_user("Other Person", "other@example.com", "otherpass1")
    login(client)
    response = post_edit(client, name="Typed Name", email="Other@Example.com")
    assert response.status_code == 400
    assert b"An account with that email already exists." in response.data
    assert b'value="Typed Name"' in response.data
    assert demo_user()["email"] == DEMO_EMAIL


def test_edit_resaving_own_email_succeeds(client):
    login(client)
    response = post_edit(client, name="Renamed", email=DEMO_EMAIL)
    assert response.status_code == 302
    assert demo_user()["name"] == "Renamed"


def test_edit_only_changes_own_row(client):
    other_id = db.create_user("Other Person", "other@example.com", "otherpass1")
    login(client)
    demo_id = demo_user()["id"]
    # A forged id field must be ignored: the session decides who is edited.
    post_edit(client, name="Changed", email="changed@example.com", id=str(other_id))

    other = fetch_user(user_id=other_id)
    assert other["name"] == "Other Person"
    assert other["email"] == "other@example.com"
    assert fetch_user(user_id=demo_id)["name"] == "Changed"


# --------------------------------------------------------- change password ----

def test_password_form_has_three_empty_fields(client):
    login(client)
    response = client.get("/profile/password")
    assert response.status_code == 200
    for name in (b"current_password", b"new_password", b"confirm_password"):
        assert b'name="' + name + b'"' in response.data
    assert b"value=" not in response.data.split(b"<form", 1)[1].split(b"</form>", 1)[0]


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"current": "wrong-password"}, b"Current password is incorrect."),
        ({"new": "short", "confirm": "short"}, b"Password must be at least 8 characters."),
        ({"confirm": "does-not-match"}, b"New passwords do not match."),
    ],
)
def test_password_failures_return_400_and_keep_hash(client, kwargs, message):
    login(client)
    before = demo_user()["password_hash"]
    response = post_password(client, **kwargs)
    assert response.status_code == 400
    assert message in response.data
    assert demo_user()["password_hash"] == before


def test_password_same_as_current_returns_400(client):
    # The demo password is only 7 characters, so use a user whose current
    # password is long enough to pass the length check.
    db.create_user("Long Pass", "long@example.com", LONG_PASSWORD)
    login(client, email="long@example.com", password=LONG_PASSWORD)
    before = fetch_user(email="long@example.com")["password_hash"]
    response = post_password(client, current=LONG_PASSWORD, new=LONG_PASSWORD)
    assert response.status_code == 400
    assert b"New password must be different from your current password." in response.data
    assert fetch_user(email="long@example.com")["password_hash"] == before


def test_password_failure_messages_are_distinct(client):
    db.create_user("Long Pass", "long@example.com", LONG_PASSWORD)
    login(client, email="long@example.com", password=LONG_PASSWORD)
    messages = set()
    for kwargs in (
        {"current": "wrong-password", "new": NEW_PASSWORD},
        {"current": LONG_PASSWORD, "new": "short", "confirm": "short"},
        {"current": LONG_PASSWORD, "new": NEW_PASSWORD, "confirm": "does-not-match"},
        {"current": LONG_PASSWORD, "new": LONG_PASSWORD},
    ):
        body = post_password(client, **kwargs).data
        messages.add(body.split(b'class="auth-error">', 1)[1].split(b"</div>", 1)[0])
    assert len(messages) == 4


def test_password_success_changes_login_credentials(client):
    login(client)
    response = post_password(client)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")
    assert check_password_hash(demo_user()["password_hash"], NEW_PASSWORD)

    client.get("/logout")
    assert login(client, password=DEMO_PASSWORD).status_code == 400
    assert login(client, password=NEW_PASSWORD).status_code == 302


def test_password_success_leaves_only_user_id_in_session(client):
    login(client)
    with client.session_transaction() as sess:
        sess["stray"] = "value"
    post_password(client)
    with client.session_transaction() as sess:
        assert set(sess.keys()) == {"user_id"}
        assert sess["user_id"] == demo_user()["id"]


# ------------------------------------------------------ leakage and links ----

def test_no_hash_or_password_in_responses(client):
    login(client)
    bodies = [
        client.get("/profile").data,
        client.get("/profile/edit").data,
        client.get("/profile/password").data,
        post_password(client, current="wrong-password", new="typed-secret-1").data,
        post_edit(client, email="not-an-email").data,
    ]
    stored_hash = demo_user()["password_hash"].encode()
    for body in bodies:
        assert stored_hash not in body
        assert b"scrypt:" not in body
        assert b"pbkdf2:" not in body
        assert b"typed-secret-1" not in body
        assert b"wrong-password" not in body


def test_profile_page_links_to_new_pages(client):
    login(client)
    page = client.get("/profile")
    assert b'href="/profile/edit"' in page.data
    assert b'href="/profile/password"' in page.data
