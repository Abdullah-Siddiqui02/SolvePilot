
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

    # Daily Challenge - Same for everyone today
    import hashlib
    from datetime import date
    today_str = date.today().strftime("%Y-%m-%d")
    seed = int(hashlib.md5(today_str.encode()).hexdigest(), 16) % 100 # Mod by total problems approx
    cursor.execute("SELECT id, title, difficulty, tags FROM global_problems LIMIT 1 OFFSET %s", (seed,))
    daily_challenge = cursor.fetchone()

    # Check if user solved today's challenge
    is_challenge_solved = False
    if daily_challenge:
        cursor.execute("SELECT status FROM user_collection WHERE user_id=%s AND problem_id=%s", (user_id, daily_challenge[0]))
        res = cursor.fetchone()
        if res and res[0] == 'solved':
            is_challenge_solved = True

    # User Info (Streak & Rank)
    cursor.execute("SELECT current_streak FROM users WHERE id = %s", (user_id,))
    user_streak = cursor.fetchone()[0]

    # Leaderboard - Top 5 users
    cursor.execute("""
        SELECT u.username, COUNT(uc.id) as solved_count, u.current_streak
        FROM users u
        LEFT JOIN user_collection uc ON u.id = uc.user_id AND uc.status = 'solved'
        GROUP BY u.id
        ORDER BY solved_count DESC, u.current_streak DESC
        LIMIT 5
    """)
    leaderboard = cursor.fetchall()

    # Difficulty Progress Stats
    diff_stats = {}
    for diff in ['Easy', 'Medium', 'Hard']:
        cursor.execute("SELECT COUNT(*) FROM global_problems WHERE difficulty = %s", (diff,))
        t_bank = cursor.fetchone()[0]
        cursor.execute("""
            SELECT COUNT(*) FROM user_collection uc 
            JOIN global_problems gp ON uc.problem_id = gp.id 
            WHERE uc.user_id = %s AND gp.difficulty = %s AND uc.status = 'solved'
        """, (user_id, diff))
        s_bank = cursor.fetchone()[0]
        diff_stats[diff] = {
            'solved': s_bank, 
            'total': t_bank, 
            'percent': int((s_bank/t_bank*100)) if t_bank > 0 else 0
        }

    # Hot Topics - Aggregate tags and fetch questions per topic
    cursor.execute("SELECT id, title, difficulty, tags FROM global_problems WHERE tags IS NOT NULL")
    all_global_problems = cursor.fetchall()
    tag_counts = {}
    tag_questions = {}
    for row in all_global_problems:
        prob_id, prob_title, prob_diff, prob_tags = row
        for tag in prob_tags.split(','):
            tag = tag.strip()
            if tag:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
                if tag not in tag_questions:
                    tag_questions[tag] = []
                if len(tag_questions[tag]) < 5:
                    tag_questions[tag].append({
                        'id': prob_id,
                        'title': prob_title,
                        'difficulty': prob_diff
                    })
    hot_topics = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:6]
    hot_topics_data = [(t, c, tag_questions.get(t, [])) for t, c in hot_topics]


    return render_template(
        "dashboard.html",
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
        leaderboard=leaderboard,
        diff_stats=diff_stats,
        hot_topics=hot_topics_data
    )
