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


@questions_bp.route("/api/my-questions", methods=["GET"])
def get_my_questions():
    if "user_id" not in session:
        return {"error": "Unauthorized"}, 401
    
    user_id = session["user_id"]
    cursor.execute(
        "SELECT id, title, topic, difficulty FROM questions WHERE user_id = %s ORDER BY created_at DESC",
        (user_id,)
    )
    rows = cursor.fetchall()
    
    # Map rows to list of dicts
    questions = []
    for r in rows:
        questions.append({
            "id": r[0],
            "title": r[1],
            "topic": r[2],
            "difficulty": r[3]
        })
        
    return {"questions": questions}
