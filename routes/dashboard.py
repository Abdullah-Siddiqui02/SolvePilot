
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

    # User Collection Progress
    cursor.execute(
        "SELECT COUNT(*) FROM user_collection WHERE user_id=%s",
        (user_id,),
    )
    total_added = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM user_collection WHERE user_id=%s AND status='solved'",
        (user_id,),
    )
    total_solved = cursor.fetchone()[0]

    # Fetch all custom questions solved by the user
    cursor.execute(
        "SELECT id, title, topic, difficulty FROM questions WHERE user_id=%s ORDER BY created_at DESC",
        (user_id,),
    )
    all_questions = cursor.fetchall()

    # Fetch collection details
    cursor.execute(
        """
        SELECT gp.title, gp.difficulty, uc.status, gp.url, gp.id
        FROM user_collection uc 
        JOIN global_problems gp ON uc.problem_id = gp.id 
        WHERE uc.user_id=%s
        ORDER BY uc.created_at DESC
        """,
        (user_id,),
    )
    collection_details = cursor.fetchall()

    return render_template(
        "dashboard.html",
        total=total,
        topics=topics,
        difficulties=difficulties,
        total_added=total_added,
        total_solved=total_solved,
        all_questions=all_questions,
        collection_details=collection_details,
    )
