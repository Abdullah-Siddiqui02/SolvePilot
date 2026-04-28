from collections import defaultdict
from datetime import date, timedelta
import hashlib

from flask import Blueprint, redirect, render_template, session

from extensions import cursor

dashboard_bp = Blueprint("dashboard", __name__)


def _relative_time_label(created_at):
    today = date.today()
    event_day = created_at.date() if hasattr(created_at, "date") else created_at
    days_ago = (today - event_day).days

    if days_ago <= 0:
        return "Today"
    if days_ago == 1:
        return "1d ago"
    if days_ago < 7:
        return f"{days_ago}d ago"
    return event_day.strftime("%d %b")


@dashboard_bp.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/")

    user_id = session["user_id"]
    today = date.today()

    cursor.execute(
        "SELECT username, current_streak, last_solved_date FROM users WHERE id = %s",
        (user_id,),
    )
    user_row = cursor.fetchone()
    username = user_row[0]
    user_streak = user_row[1] or 0
    last_solved_date = user_row[2]

    # Break the streak if the user missed a day
    if last_solved_date is None or (last_solved_date != today and last_solved_date != today - timedelta(days=1)):
        if user_streak != 0:
            user_streak = 0
            cursor.execute(
                "UPDATE users SET current_streak = 0 WHERE id = %s",
                (user_id,),
            )
            cursor.connection.commit()

    cursor.execute(
        "SELECT COUNT(*) FROM questions WHERE user_id=%s",
        (user_id,),
    )
    total = cursor.fetchone()[0]

    cursor.execute(
        "SELECT topic, COUNT(*) FROM questions WHERE user_id=%s GROUP BY topic ORDER BY COUNT(*) DESC, topic ASC",
        (user_id,),
    )
    topics = cursor.fetchall()

    cursor.execute(
        "SELECT difficulty, COUNT(*) FROM questions WHERE user_id=%s GROUP BY difficulty",
        (user_id,),
    )
    difficulties = cursor.fetchall()

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

    cursor.execute(
        "SELECT id, title, topic, difficulty FROM questions WHERE user_id=%s ORDER BY created_at DESC",
        (user_id,),
    )
    all_questions = cursor.fetchall()

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

    cursor.execute("SELECT COUNT(*) FROM global_problems")
    global_problem_count = cursor.fetchone()[0]
    daily_challenge = None
    if global_problem_count:
        today_str = today.strftime("%Y-%m-%d")
        seed = int(hashlib.md5(today_str.encode()).hexdigest(), 16) % global_problem_count
        cursor.execute(
            "SELECT id, title, difficulty, tags FROM global_problems LIMIT 1 OFFSET %s",
            (seed,),
        )
        daily_challenge = cursor.fetchone()

    is_challenge_solved = False
    if daily_challenge:
        cursor.execute(
            "SELECT status FROM user_collection WHERE user_id=%s AND problem_id=%s",
            (user_id, daily_challenge[0]),
        )
        challenge_status = cursor.fetchone()
        if challenge_status and challenge_status[0] == "solved":
            is_challenge_solved = True



    diff_stats = {}
    for diff in ["Easy", "Medium", "Hard"]:
        cursor.execute("SELECT COUNT(*) FROM global_problems WHERE difficulty = %s", (diff,))
        total_bank = cursor.fetchone()[0]
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM user_collection uc
            JOIN global_problems gp ON uc.problem_id = gp.id
            WHERE uc.user_id = %s AND gp.difficulty = %s AND uc.status = 'solved'
            """,
            (user_id, diff),
        )
        solved_bank = cursor.fetchone()[0]
        diff_stats[diff] = {
            "solved": solved_bank,
            "total": total_bank,
            "percent": int((solved_bank / total_bank) * 100) if total_bank else 0,
        }

    # Weekly progress for line chart
    cursor.execute(
        """
        SELECT DATE(created_at) AS solved_on, COUNT(*)
        FROM user_collection
        WHERE user_id = %s AND status = 'solved' AND created_at >= %s
        GROUP BY DATE(created_at)
        ORDER BY solved_on ASC
        """,
        (user_id, today - timedelta(days=6)),
    )
    weekly_rows = cursor.fetchall()
    weekly_map = {row[0]: row[1] for row in weekly_rows}
    weekly_progress = []
    weekly_total = 0
    for offset in range(6, -1, -1):
        current_day = today - timedelta(days=offset)
        solved_count = weekly_map.get(current_day, 0)
        weekly_total += solved_count
        weekly_progress.append({"label": current_day.strftime("%a"), "value": solved_count})


    cursor.execute("SELECT id, title, difficulty, tags FROM global_problems WHERE tags IS NOT NULL")
    all_global_problems = cursor.fetchall()
    tag_totals = defaultdict(int)
    tag_questions = defaultdict(list)
    for problem_id, title, difficulty, raw_tags in all_global_problems:
        for tag in raw_tags.split(","):
            clean_tag = tag.strip()
            if not clean_tag:
                continue
            tag_totals[clean_tag] += 1
            if len(tag_questions[clean_tag]) < 5:
                tag_questions[clean_tag].append(
                    {"id": problem_id, "title": title, "difficulty": difficulty}
                )

    hot_topics = sorted(tag_totals.items(), key=lambda item: (-item[1], item[0]))[:6]
    hot_topics_data = [(topic, count, tag_questions.get(topic, [])) for topic, count in hot_topics]

    cursor.execute(
        """
        SELECT gp.tags
        FROM user_collection uc
        JOIN global_problems gp ON uc.problem_id = gp.id
        WHERE uc.user_id = %s AND uc.status = 'solved' AND gp.tags IS NOT NULL
        """,
        (user_id,),
    )
    solved_tag_counts = defaultdict(int)
    for (raw_tags,) in cursor.fetchall():
        for tag in raw_tags.split(","):
            clean_tag = tag.strip()
            if clean_tag:
                solved_tag_counts[clean_tag] += 1

    topic_mastery = []
    mastery_candidates = sorted(
        tag_totals.items(),
        key=lambda item: (-solved_tag_counts.get(item[0], 0), -item[1], item[0]),
    )[:4]
    mastery_sum = 0
    for topic_name, total_count in mastery_candidates:
        solved_count = solved_tag_counts.get(topic_name, 0)
        percent = int((solved_count / total_count) * 100) if total_count else 0
        mastery_sum += percent
        topic_mastery.append(
            {"name": topic_name, "solved": solved_count, "total": total_count, "percent": percent}
        )

    overall_mastery = int(mastery_sum / len(topic_mastery)) if topic_mastery else 0

    weak_topics = sorted(
        [
            {
                "name": topic_name,
                "percent": int((solved_tag_counts.get(topic_name, 0) / total_count) * 100) if total_count else 0,
            }
            for topic_name, total_count in tag_totals.items()
            if total_count >= 2
        ],
        key=lambda item: (item["percent"], item["name"]),
    )[:3]

    recommended_problem = None
    weak_topic_names = [item["name"] for item in weak_topics]
    if weak_topic_names:
        like_conditions = " OR ".join(["gp.tags LIKE %s"] * len(weak_topic_names))
        like_values = [f"%{topic_name}%" for topic_name in weak_topic_names]
        cursor.execute(
            f"""
            SELECT gp.id, gp.title, gp.difficulty, gp.tags
            FROM global_problems gp
            WHERE ({like_conditions})
              AND gp.id NOT IN (
                  SELECT problem_id FROM user_collection WHERE user_id = %s
              )
            ORDER BY FIELD(gp.difficulty, 'Medium', 'Easy', 'Hard'), gp.id DESC
            LIMIT 1
            """,
            tuple(like_values + [user_id]),
        )
        recommended_problem = cursor.fetchone()

    if not recommended_problem:
        cursor.execute(
            """
            SELECT gp.id, gp.title, gp.difficulty, gp.tags
            FROM global_problems gp
            WHERE gp.id NOT IN (
                SELECT problem_id FROM user_collection WHERE user_id = %s
            )
            ORDER BY FIELD(gp.difficulty, 'Medium', 'Easy', 'Hard'), gp.id DESC
            LIMIT 1
            """,
            (user_id,),
        )
        recommended_problem = cursor.fetchone()

    recent_activity = []
    cursor.execute(
        """
        SELECT gp.title, gp.tags, uc.status, uc.created_at
        FROM user_collection uc
        JOIN global_problems gp ON uc.problem_id = gp.id
        WHERE uc.user_id = %s
        ORDER BY uc.created_at DESC
        LIMIT 4
        """,
        (user_id,),
    )
    for title, tags, status, created_at in cursor.fetchall():
        topic_label = tags.split(",")[0].strip() if tags else "Practice"
        recent_activity.append(
            {
                "title": f"{'Solved' if status == 'solved' else 'Saved'} {title}",
                "topic": topic_label,
                "time": _relative_time_label(created_at),
                "status": status,
                "sort_at": created_at,
            }
        )

    cursor.execute(
        """
        SELECT title, topic, created_at
        FROM questions
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT 3
        """,
        (user_id,),
    )
    for title, topic, created_at in cursor.fetchall():
        recent_activity.append(
            {
                "title": f"Added {title}",
                "topic": topic,
                "time": _relative_time_label(created_at),
                "status": "added",
                "sort_at": created_at,
            }
        )

    recent_activity = sorted(recent_activity, key=lambda item: item["sort_at"], reverse=True)[:4]

    return render_template(
        "dashboard.html",
        username=username,
        total=total,
        topics=topics,
        difficulties=difficulties,
        total_added=total_added,
        total_solved=total_solved,
        all_questions=all_questions,
        collection_details=collection_details,
        daily_challenge=daily_challenge,
        is_challenge_solved=is_challenge_solved,
        user_streak=user_streak,
        diff_stats=diff_stats,
        hot_topics=hot_topics_data,
        weekly_progress=weekly_progress,
        weekly_total=weekly_total,
        topic_mastery=topic_mastery,
        overall_mastery=overall_mastery,
        weak_topics=weak_topics,
        recommended_problem=recommended_problem,
        recent_activity=recent_activity,
    )
