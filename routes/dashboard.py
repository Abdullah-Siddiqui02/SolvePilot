"""
Dashboard route: shows question stats for the logged-in user.
"""

from flask import Blueprint, render_template, redirect, session
from extensions import cursor

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/")

    user_id = session["user_id"]

    # Total questions
    cursor.execute(
        "SELECT COUNT(*) FROM questions WHERE user_id=%s",
        (user_id,),
    )
    total = cursor.fetchone()[0]

    # Questions grouped by topic
    cursor.execute(
        "SELECT topic, COUNT(*) FROM questions WHERE user_id=%s GROUP BY topic",
        (user_id,),
    )
    topics = cursor.fetchall()

    # Questions grouped by difficulty
    cursor.execute(
        "SELECT difficulty, COUNT(*) FROM questions WHERE user_id=%s GROUP BY difficulty",
        (user_id,),
    )
    difficulties = cursor.fetchall()

    return render_template(
        "dashboard.html",
        total=total,
        topics=topics,
        difficulties=difficulties,
    )
