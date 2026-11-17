from conftest import login, set_session_user  # noqa: F401


def test_get_login_renders_form(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b'action="/login"' in response.data


def test_valid_login_redirects_to_profile_and_sets_session(client):
    response = login(client)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")
    with client.session_transaction() as sess:
        assert sess.get("user_id") is not None


def test_wrong_password_and_unknown_email_share_message(client):
    wrong = login(client, password="not-the-password")
    unknown = login(client, email="nobody@example.com")
    assert wrong.status_code == 400
    assert unknown.status_code == 400
    assert b"Invalid email or password." in wrong.data
    assert b"Invalid email or password." in unknown.data
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_email_is_trimmed_and_case_insensitive(client):
    response = login(client, email="  Demo@Spendly.com ")
    assert response.status_code == 302


def test_failed_login_prefills_email_not_password(client):
    response = login(client, email="demo@spendly.com", password="wrong-pass-123")
    assert b'value="demo@spendly.com"' in response.data
    assert b"wrong-pass-123" not in response.data


def test_registered_user_can_log_in(client):
    client.post(
        "/register",
        data={"name": "New User", "email": "new@example.com", "password": "password123"},
    )
    response = login(client, email="new@example.com", password="password123")
    assert response.status_code == 302


def test_logged_in_get_login_redirects_to_profile(client):
    login(client)
    response = client.get("/login")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")


def test_logout_clears_session_and_redirects_home(client):
    login(client)
    response = client.get("/logout")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_navbar_reflects_login_state(client):
    logged_out = client.get("/").data
    assert b"Sign in" in logged_out and b"Get started" in logged_out
    assert b"Sign out" not in logged_out

    login(client)
    logged_in = client.get("/terms").data
    assert b"Sign out" in logged_in and b"Profile" in logged_in
    assert b"Get started" not in logged_in


def test_no_password_hash_in_pages(client):
    login(client)
    for path in ("/", "/login", "/terms"):
        assert b"pbkdf2:" not in client.get(path).data
        assert b"scrypt:" not in client.get(path).data
