from database import db

from conftest import login


def test_get_login_renders_form_with_url_for_action(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b'action="/login"' in response.data


def test_successful_login_redirects_to_profile_and_sets_session(client):
    response = login(client)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")

    with client.session_transaction() as sess:
        assert sess["user_id"] == db.get_user_by_email("demo@spendly.com")["id"]


def test_login_email_is_case_and_whitespace_insensitive(client):
    response = login(client, email="  DEMO@Spendly.com ")
    assert response.status_code == 302


def test_wrong_password_rejected(client):
    response = login(client, password="wrong-password")
    assert response.status_code == 400
    assert b"Invalid email or password." in response.data
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_unknown_email_gets_same_message(client):
    response = login(client, email="nobody@example.com")
    assert response.status_code == 400
    assert b"Invalid email or password." in response.data


def test_failed_login_prefills_email_but_not_password(client):
    response = login(client, email="demo@spendly.com", password="wrong-password")
    assert b'value="demo@spendly.com"' in response.data
    assert b"wrong-password" not in response.data


def test_missing_fields_return_400_not_500(client):
    assert client.post("/login", data={}).status_code == 400


def test_logout_clears_session_and_redirects_to_landing(client):
    login(client)
    response = client.get("/logout")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_login_page_redirects_when_already_logged_in(client):
    login(client)
    response = client.get("/login")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")


def test_register_then_login_end_to_end(client):
    client.post(
        "/register",
        data={"name": "Sara Malik", "email": "sara@example.com", "password": "password123"},
    )
    response = login(client, email="sara@example.com", password="password123")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")
