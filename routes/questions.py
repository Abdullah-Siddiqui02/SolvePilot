"""
Question management routes: adding new questions.
"""

from flask import Blueprint, render_template, request, redirect, session, flash
from extensions import db, cursor

questions_bp = Blueprint("questions", __name__)


@questions_bp.route("/add", methods=["GET", "POST"])
def add():
    if "user_id" not in session:
        return redirect("/")

    if request.method == "POST":
        title      = request.form["title"]
        topic      = request.form["topic"]
        difficulty = request.form["difficulty"]
        user_id    = session["user_id"]

        cursor.execute(
            "INSERT INTO questions (user_id, title, topic, difficulty) VALUES (%s, %s, %s, %s)",
            (user_id, title, topic, difficulty),
        )
        db.commit()

        flash("Question added successfully!", "success")
        return redirect("/dashboard")

    return render_template("add_question.html")
