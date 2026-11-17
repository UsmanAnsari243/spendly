import importlib

import pytest

from database import db


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Test client backed by a throwaway DB so the real spendly.db is never touched."""
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))

    import app as app_module

    # Reloading re-runs init_db()/seed_db() against the patched DB_PATH.
    importlib.reload(app_module)
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


def login(client, email="demo@spendly.com", password="demo123"):
    return client.post("/login", data={"email": email, "password": password})


def set_session_user(client, user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
