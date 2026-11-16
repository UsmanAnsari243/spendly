import os
import sqlite3
from datetime import datetime

from flask import Flask, abort, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from database.db import (
    create_user,
    get_category_breakdown,
    get_db,  # noqa: F401  (used in later steps)
    get_expense_summary,
    get_recent_expenses,
    get_user_by_email,
    get_user_by_id,
    init_db,
    seed_db,
)

app = Flask(__name__)
# Set SECRET_KEY in the environment for any real deployment; the fallback is dev-only.
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or "dev-only-insecure-key"

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Presentation helpers                                                #
# ------------------------------------------------------------------ #

def format_pkr(amount):
    """Format an amount as PKR with thousands separators; paise only if non-zero."""
    amount = float(amount or 0)
    if amount.is_integer():
        return f"PKR {int(amount):,}"
    return f"PKR {amount:,.2f}"


app.add_template_filter(format_pkr, "pkr")


def build_initials(name):
    """Return up to two uppercase initials from a name, or '?' if there are none."""
    letters = [word[0] for word in name.split()[:2]]
    return "".join(letters).upper() or "?"


def format_member_since(created_at):
    """Turn a 'YYYY-MM-DD HH:MM:SS' timestamp into 'Month YYYY' ('' if unparseable)."""
    try:
        return datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S").strftime("%B %Y")
    except (TypeError, ValueError):
        return ""


def round_percentages(totals):
    """Return integer percentages of the totals that sum to exactly 100.

    Uses the largest-remainder method. An empty or all-zero input yields zeros.
    """
    grand_total = sum(totals)
    if grand_total <= 0:
        return [0 for _ in totals]

    exact = [total / grand_total * 100 for total in totals]
    floors = [int(value) for value in exact]
    leftover = 100 - sum(floors)
    by_remainder = sorted(
        range(len(totals)), key=lambda i: exact[i] - floors[i], reverse=True
    )
    for index in by_remainder[:leftover]:
        floors[index] += 1
    return floors


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

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    def form_error(message):
        return render_template("register.html", error=message, name=name, email=email), 400

    if not name:
        return form_error("Name is required.")

    local, separator, domain = email.partition("@")
    if not (local and separator and domain):
        return form_error("Please enter a valid email address.")

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


@app.route("/profile")
def profile():
    user_id = session.get("user_id")
    if user_id is None:
        return redirect(url_for("login"))

    user = get_user_by_id(user_id)
    if user is None:
        abort(404)

    summary = get_expense_summary(user_id)
    breakdown_rows = get_category_breakdown(user_id)
    percentages = round_percentages([row["total"] for row in breakdown_rows])
    breakdown = [
        {
            "category": row["category"],
            "total": row["total"],
            "count": row["count"],
            "pct": pct,
            "width": row["total"] / summary["total"] * 100 if summary["total"] else 0,
        }
        for row, pct in zip(breakdown_rows, percentages)
    ]

    return render_template(
        "profile.html",
        user=user,
        initials=build_initials(user["name"]),
        member_since=format_member_since(user["created_at"]),
        summary=summary,
        breakdown=breakdown,
        top_category=breakdown[0]["category"] if breakdown else None,
        recent=get_recent_expenses(user_id),
    )


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
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
