from flask import Blueprint, jsonify, request, session
from extensions import get_db

collection_bp = Blueprint("collection", __name__)

@collection_bp.route("/api/collection/add", methods=["POST"])
def add_to_collection():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    problem_id = data.get("problem_id")
    user_id = session["user_id"]
    
    if not problem_id:
        return jsonify({"error": "Problem ID is required"}), 400
    
    db, cursor = get_db()
    try:
        cursor.execute(
            "INSERT INTO user_collection (user_id, problem_id) VALUES (%s, %s)",
            (user_id, problem_id)
        )
        db.commit()
        return jsonify({"message": "Problem added to collection"}), 201
    except Exception as e:
        if "Duplicate entry" in str(e):
            return jsonify({"message": "Problem already in collection"}), 200
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()

@collection_bp.route("/api/collection", methods=["GET"])
def get_collection():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    user_id = session["user_id"]
    db, cursor = get_db()
    
    query = """
        SELECT gp.id, gp.title, gp.difficulty, gp.platform, gp.url, uc.status
        FROM global_problems gp
        JOIN user_collection uc ON gp.id = uc.problem_id
        WHERE uc.user_id = %s
        ORDER BY uc.created_at DESC
    """
    cursor.execute(query, (user_id,))
    rows = cursor.fetchall()
    
    column_names = [col[0] for col in cursor.description]
    problems = [dict(zip(column_names, row)) for row in rows]
    
    cursor.close()
    return jsonify({"problems": problems})

@collection_bp.route("/api/collection/toggle-status", methods=["POST"])
def toggle_status():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    problem_id = data.get("problem_id")
    current_status = data.get("status")
    user_id = session["user_id"]
    
    if not problem_id or not current_status:
        return jsonify({"error": "Problem ID and current status are required"}), 400
    
    new_status = "solved" if current_status == "added" else "added"
    
    db, cursor = get_db()
    try:
        cursor.execute(
            "UPDATE user_collection SET status = %s WHERE user_id = %s AND problem_id = %s",
            (new_status, user_id, problem_id)
        )
        
        if new_status == 'solved':
            from datetime import date, timedelta
            today = date.today()
            
            # Fetch current streak info
            cursor.execute("SELECT last_solved_date, current_streak FROM users WHERE id = %s", (user_id,))
            user_data = cursor.fetchone()
            last_date = user_data[0]
            streak = user_data[1]
            
            if last_date == today:
                pass # Already solved something today
            elif last_date == today - timedelta(days=1):
                streak += 1
            else:
                streak = 1 # Streak reset or started
            
            cursor.execute(
                "UPDATE users SET last_solved_date = %s, current_streak = %s WHERE id = %s",
                (today, streak, user_id)
            )

        db.commit()
        return jsonify({"message": f"Status updated to {new_status}", "new_status": new_status})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
@collection_bp.route("/api/collection/remove", methods=["POST"])
def remove_from_collection():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    problem_id = data.get("problem_id")
    user_id = session["user_id"]
    
    if not problem_id:
        return jsonify({"error": "Problem ID is required"}), 400
    
    db, cursor = get_db()
    try:
        cursor.execute(
            "DELETE FROM user_collection WHERE user_id = %s AND problem_id = %s",
            (user_id, problem_id)
        )
        db.commit()
        return jsonify({"message": "Problem removed from collection"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
