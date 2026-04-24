from flask import Blueprint, jsonify, request, session
from extensions import get_db
import requests
from datetime import date, timedelta

submit_bp = Blueprint("submit", __name__)

WANDBOX_COMPILE_URL = "https://wandbox.org/api/compile.json"

COMPILER_MAP = {
    "python":     "cpython-3.12.7",
    "javascript": "nodejs-18.20.4",
    "java":       "openjdk-jdk-21+35",
    "cpp":        "gcc-13.2.0"
}

@submit_bp.route("/api/submit", methods=["POST"])
def submit_solution():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    problem_id = data.get("problem_id")
    code = data.get("code")
    language = data.get("language", "").lower()
    user_id = session["user_id"]
    
    if not problem_id or not code or not language:
        return jsonify({"error": "Missing required fields"}), 400

    if language not in COMPILER_MAP:
        return jsonify({"error": f"Unsupported language: {language}"}), 400

    # Prepare payload for Wandbox
    payload = {
        "compiler": COMPILER_MAP[language],
        "code": code,
        "save": False
    }
    if language == "cpp":
        payload["options"] = "warning,gnu++17"

    try:
        response = requests.post(WANDBOX_COMPILE_URL, json=payload, timeout=30)
        
        if response.status_code != 200:
            return jsonify({"error": "Execution engine error", "details": response.text}), 500
            
        result = response.json()
        exit_status = result.get("status", "0")
        
        # In this system, "Accepted" means exit status 0 (no errors)
        is_accepted = (exit_status == "0" or exit_status == 0) and not result.get("compiler_error") and not result.get("program_error")
        
        if is_accepted:
            db, cursor = get_db()
            
            # Check if problem is in collection
            cursor.execute(
                "SELECT status FROM user_collection WHERE user_id = %s AND problem_id = %s",
                (user_id, problem_id)
            )
            row = cursor.fetchone()
            
            if row:
                # Update status
                cursor.execute(
                    "UPDATE user_collection SET status = 'solved' WHERE user_id = %s AND problem_id = %s",
                    (user_id, problem_id)
                )
                
                # Update streak logic
                today = date.today()
                cursor.execute("SELECT last_solved_date, current_streak FROM users WHERE id = %s", (user_id,))
                user_data = cursor.fetchone()
                last_date = user_data[0]
                streak = user_data[1] or 0
                
                if last_date == today:
                    pass 
                elif last_date == today - timedelta(days=1):
                    streak += 1
                else:
                    streak = 1
                
                cursor.execute(
                    "UPDATE users SET last_solved_date = %s, current_streak = %s WHERE id = %s",
                    (today, streak, user_id)
                )
                
                db.commit()
                cursor.close()
                return jsonify({
                    "status": "Accepted",
                    "output": result.get("program_output", ""),
                    "message": "Problem solved! Your collection and streak have been updated."
                })
            else:
                cursor.close()
                return jsonify({
                    "status": "Accepted",
                    "output": result.get("program_output", ""),
                    "message": "Solution correct, but problem was not in your collection."
                })
        else:
            # Not accepted
            stderr = result.get("compiler_error") or result.get("program_error") or ""
            return jsonify({
                "status": "Error",
                "output": result.get("program_output", ""),
                "stderr": stderr,
                "message": "Submission failed. Please check your code for errors."
            })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
