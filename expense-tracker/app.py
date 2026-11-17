import math
import os
import sqlite3
from datetime import date, datetime

from flask import Flask, abort, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from database.db import (  # noqa: F401  (get_db used in later steps)
    create_user,
    get_category_breakdown,
    get_db,
    get_expense_summary,
    get_expenses_between,
    get_password_hash,
    get_recent_expenses,
    get_user_by_email,
    get_user_by_id,
    init_db,
    seed_db,
    update_password,
    update_user,
)

app = Flask(__name__)
# Development fallback only; set SECRET_KEY in the environment for real use.
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-insecure-key")


@app.context_processor
def inject_auth_state():
    return {"logged_in": session.get("user_id") is not None}


# ------------------------------------------------------------------ #
# Template helpers (presentation only, no DB access)                  #
# ------------------------------------------------------------------ #

@app.template_filter("pkr")
def format_pkr(amount):
    amount = round(float(amount or 0), 2)
    if amount == int(amount):
        return f"PKR {int(amount):,}"
    return f"PKR {amount:,.2f}"


@app.template_filter("initials")
def initials(name):
    words = (name or "").split()
    if not words:
        return "?"
    if len(words) == 1:
        return words[0][0].upper()
    return (words[0][0] + words[-1][0]).upper()


@app.template_filter("member_since")
def member_since(created_at):
    try:
        return datetime.strptime((created_at or "")[:10], "%Y-%m-%d").strftime("%B %Y")
    except ValueError:
        return ""


def parse_period(start_raw, end_raw):
    """Validate a from/to pair; return (start, end, error).

    Both empty means no period was chosen: (None, None, None).
    """
    if not start_raw and not end_raw:
        return None, None, None
    if not start_raw or not end_raw:
        return None, None, "Please choose both a start and an end date."
    try:
        start = date.fromisoformat(start_raw)
        end = date.fromisoformat(end_raw)
    except ValueError:
        return None, None, "Please enter valid dates."
    if start > end:
        return None, None, "The start date must be on or before the end date."
    return start.isoformat(), end.isoformat(), None


def with_percentages(rows, total):
    """Attach integer percentages that sum to exactly 100 (largest remainder)."""
    if not rows or not total:
        return []
    raw = [row["total"] * 100 / total for row in rows]
    pcts = [math.floor(value) for value in raw]
    leftover = 100 - sum(pcts)
    by_remainder = sorted(range(len(raw)), key=lambda i: (-(raw[i] - pcts[i]), i))
    for i in by_remainder[:leftover]:
        pcts[i] += 1
    return [
        {"category": row["category"], "total": row["total"], "count": row["count"], "pct": pct}
        for row, pct in zip(rows, pcts)
    ]


def load_session_user():
    """Return the logged-in user row.

    Aborts with a redirect to /login when nobody is logged in, and with 404
    when the session points at a user that no longer exists.
    """
    user_id = session.get("user_id")
    if user_id is None:
        abort(redirect(url_for("login")))
    user = get_user_by_id(user_id)
    if user is None:
        abort(404)
    return user


def validate_name_email(name_raw, email_raw):
    """Normalise and validate a name/email pair; return (name, email, error)."""
    name = name_raw.strip()
    email = email_raw.strip().lower()

    if not name:
        return name, email, "Name is required."

    local, separator, domain = email.partition("@")
    if not (local and separator and domain):
        return name, email, "Please enter a valid email address."

    return name, email, None


with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    name, email, error = validate_name_email(
        request.form.get("name", ""), request.form.get("email", "")
    )
    password = request.form.get("password", "")

    def form_error(message):
        return render_template("register.html", error=message, name=name, email=email), 400

    if error:
        return form_error(error)

    if len(password) < 8:
        return form_error("Password must be at least 8 characters.")

    try:
        create_user(name, email, password)
    except sqlite3.IntegrityError:
        return form_error("An account with that email already exists.")

    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if session.get("user_id") is not None:
            return redirect(url_for("profile"))
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    user = get_user_by_email(email)
    if user is None or not check_password_hash(user["password_hash"], password):
        # Same message for unknown email and wrong password: no account enumeration.
        return (
            render_template("login.html", error="Invalid email or password.", email=email),
            400,
        )

    session.clear()
    session["user_id"] = user["id"]
    return redirect(url_for("profile"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Profile                                                             #
# ------------------------------------------------------------------ #

@app.route("/profile")
def profile():
    user = load_session_user()
    user_id = user["id"]

    start_raw = request.args.get("from", "").strip()
    end_raw = request.args.get("to", "").strip()
    period_start, period_end, period_error = parse_period(start_raw, end_raw)

    # With a valid range, every stat is limited to it; "this month" becomes
    # the month of the range's end date.
    month = period_end[:7] if period_end else None
    summary = get_expense_summary(user_id, month, period_start, period_end)
    breakdown = with_percentages(
        get_category_breakdown(user_id, period_start, period_end), summary["total"]
    )
    month_label = (
        datetime.strptime(month, "%Y-%m").strftime("%B %Y") if month else "This month"
    )

    period_expenses = None
    if period_start is not None:
        period_expenses = get_expenses_between(user_id, period_start, period_end)

    return render_template(
        "profile.html",
        user=user,
        summary=summary,
        month_label=month_label,
        breakdown=breakdown,
        top=breakdown[0] if breakdown else None,
        recent=get_recent_expenses(user_id),
        today=date.today().isoformat(),
        period_from=start_raw,
        period_to=end_raw,
        period_error=period_error,
        period_expenses=period_expenses,
        period_total=sum(e["amount"] for e in period_expenses) if period_expenses else 0,
    )


@app.route("/profile/edit", methods=["GET", "POST"])
def edit_profile():
    user = load_session_user()

    if request.method == "GET":
        return render_template("profile_edit.html", name=user["name"], email=user["email"])

    name, email, error = validate_name_email(
        request.form.get("name", ""), request.form.get("email", "")
    )

    def form_error(message):
        return render_template("profile_edit.html", error=message, name=name, email=email), 400

    if error:
        return form_error(error)

    try:
        updated = update_user(user["id"], name, email)
    except sqlite3.IntegrityError:
        return form_error("An account with that email already exists.")

    if not updated:
        abort(404)
    return redirect(url_for("profile"))


@app.route("/profile/password", methods=["GET", "POST"])
def change_password():
    user = load_session_user()

    if request.method == "GET":
        return render_template("profile_password.html")

    stored_hash = get_password_hash(user["id"])
    if stored_hash is None:
        abort(404)

    # Passwords are compared exactly as typed: never stripped or normalised.
    current = request.form.get("current_password", "")
    new = request.form.get("new_password", "")
    confirm = request.form.get("confirm_password", "")

    def form_error(message):
        return render_template("profile_password.html", error=message), 400

    if not check_password_hash(stored_hash, current):
        return form_error("Current password is incorrect.")
    if len(new) < 8:
        return form_error("Password must be at least 8 characters.")
    if new != confirm:
        return form_error("New passwords do not match.")
    if check_password_hash(stored_hash, new):
        return form_error("New password must be different from your current password.")

    if not update_password(user["id"], new):
        abort(404)

    # Rotate the session so it carries only the user id.
    session.clear()
    session["user_id"] = user["id"]
    return redirect(url_for("profile"))


# ------------------------------------------------------------------ #
# Placeholder routes — implemented in later steps                     #
# ------------------------------------------------------------------ #

@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:expense_id>/edit")
def edit_expense(expense_id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:expense_id>/delete")
def delete_expense(expense_id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
