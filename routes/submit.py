from flask import Blueprint, jsonify, request, session
from extensions import get_db, groq_client
import requests
import json
import traceback
from bs4 import BeautifulSoup
from datetime import date, timedelta

submit_bp = Blueprint("submit", __name__)

WANDBOX_COMPILE_URL = "https://wandbox.org/api/compile.json"

COMPILER_MAP = {
    "python":     "cpython-3.12.7",
    "javascript": "nodejs-18.20.4",
    "java":       "openjdk-jdk-21+35",
    "cpp":        "gcc-13.2.0"
}

import cloudscraper
 
def fetch_problem_description(url):
    """Attempt to scrape problem description if missing."""
    try:
        scraper = cloudscraper.create_scraper()
        response = scraper.get(url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # Codeforces specific
            statement = soup.find('div', class_='problem-statement')
            if statement:
                # Remove unwanted sections like sample tests from the text for AI
                for div in statement.find_all('div', class_='sample-tests'):
                    div.decompose()
                return statement.get_text(separator='\n').strip()
    except:
        pass
    return None

@submit_bp.route("/api/submit", methods=["POST"])
def submit_solution():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        problem_id = data.get("problem_id")
        code = data.get("code")
        language = data.get("language", "").lower()
        user_id = session["user_id"]
        
        if not problem_id or not code or not language:
            return jsonify({"error": "Missing required fields"}), 400

        if language not in COMPILER_MAP:
            return jsonify({"error": f"Unsupported language: {language}"}), 400

        # 1. Fetch problem metadata
        db, cursor = get_db()
        cursor.execute(
            "SELECT title, description, url FROM global_problems WHERE id = %s",
            (problem_id,)
        )
        problem = cursor.fetchone()
        if not problem:
            cursor.close()
            return jsonify({"error": "Problem not found"}), 404
        
        problem_title, problem_desc, problem_url = problem

        # 2. Fallback: Fetch description if missing
        if not problem_desc or len(problem_desc) < 50:
            problem_desc = fetch_problem_description(problem_url)
            if problem_desc:
                # Cache it for future use
                cursor.execute(
                    "UPDATE global_problems SET description = %s WHERE id = %s",
                    (problem_desc, problem_id)
                )
                db.commit()
            else:
                problem_desc = "Description unavailable. Please judge based on the title: " + problem_title

        # 3. Stage 1: Execution Check
        payload = {
            "compiler": COMPILER_MAP[language],
            "code": code,
            "save": False
        }
        if language == "cpp":
            payload["options"] = "warning,gnu++17"

        exec_response = requests.post(WANDBOX_COMPILE_URL, json=payload, timeout=30)
        if exec_response.status_code != 200:
            cursor.close()
            return jsonify({"error": "Execution engine unavailable"}), 503
            
        exec_result = exec_response.json()
        exit_status = exec_result.get("status", "0")
        exec_success = (exit_status == "0" or exit_status == 0) and not exec_result.get("compiler_error") and not exec_result.get("program_error")
        
        if not exec_success:
            stderr = exec_result.get("compiler_error") or exec_result.get("program_error") or ""
            cursor.close()
            return jsonify({
                "status": "Runtime Error",
                "output": exec_result.get("program_output", ""),
                "stderr": stderr,
                "message": "Code failed to execute. Fix syntax or runtime errors first."
            })

        # 4. Stage 2: AI Logic Check
        prompt = f"""
        Act as a strict competitive programming judge. Evaluate the user's code for:
        
        PROBLEM: {problem_title}
        STATEMENT: {problem_desc}
        
        USER CODE ({language}):
        {code}
        
        Does this code correctly implement the logic required? 
        Respond ONLY with JSON: {{"decision": "Accepted" or "Rejected", "reason": "why (max 20 words)"}}
        """
        
        try:
            completion = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            ai_response = json.loads(completion.choices[0].message.content)
        except Exception as ai_err:
            cursor.close()
            return jsonify({"error": f"AI Judge failed: {str(ai_err)}"}), 500
            
        is_accepted = ai_response.get("decision") == "Accepted"

        if is_accepted:
            cursor.execute(
                "SELECT status FROM user_collection WHERE user_id = %s AND problem_id = %s",
                (user_id, problem_id)
            )
            if cursor.fetchone():
                cursor.execute(
                    "UPDATE user_collection SET status = 'solved' WHERE user_id = %s AND problem_id = %s",
                    (user_id, problem_id)
                )
                today = date.today()
                cursor.execute("SELECT last_solved_date, current_streak FROM users WHERE id = %s", (user_id,))
                user_data = cursor.fetchone()
                last_date = user_data[0]
                streak = user_data[1] or 0
                if last_date != today:
                    streak = streak + 1 if last_date == today - timedelta(days=1) else 1
                    cursor.execute("UPDATE users SET last_solved_date = %s, current_streak = %s WHERE id = %s", (today, streak, user_id))
                db.commit()

            cursor.close()
            return jsonify({
                "status": "Accepted",
                "output": exec_result.get("program_output", ""),
                "message": f"AI Judge: {ai_response.get('reason')}"
            })
        else:
            cursor.close()
            return jsonify({
                "status": "Rejected",
                "output": exec_result.get("program_output", ""),
                "message": f"Logic Mismatch: {ai_response.get('reason')}"
            })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"System error: {str(e)}"}), 500
