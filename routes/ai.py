from flask import Blueprint, jsonify, request, session
from extensions import get_db
from services.ai_service import AIService
import traceback

ai_bp = Blueprint("ai", __name__)
ai_service = AIService()


@ai_bp.route("/api/ai/ask", methods=["POST"])
def ask_ai():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        problem_id = data.get("problem_id")
        code = data.get("code")
        language = data.get("language", "python")
        user_query = data.get("query")
        chat_history = data.get("history", [])

        if not user_query:
            return jsonify({"error": "Missing user query"}), 400

        # 1. Fetch problem metadata for context
        db, cursor = get_db()
        problem_title = "Unknown Problem"
        problem_desc = "No description available."
        
        if problem_id:
            cursor.execute(
                "SELECT title, description FROM global_problems WHERE id = %s",
                (problem_id,)
            )
            problem = cursor.fetchone()
            if problem:
                problem_title, problem_desc = problem
        
        cursor.close()

        # 2. Call AI Service
        ai_response = ai_service.ask_question(
            problem_title=problem_title,
            problem_desc=problem_desc,
            code=code,
            language=language,
            user_query=user_query,
            chat_history=chat_history
        )
        
        return jsonify({
            "response": ai_response
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"System error: {str(e)}"}), 500


@ai_bp.route("/api/ai/mentor", methods=["POST"])
def mentor_review():
    if "user_id" not in session:
        return jsonify({"status": "error", "error": "Unauthorized"}), 401

    """Return structured, context-aware AI mentor feedback.

    Accepts the full execution/submission context:
        problem_id (str|int):     The problem's database ID.
        problem_statement (str):  The problem description text.
        code (str):               The student's current editor code.
        language (str):           Programming language.
        action_type (str):        'run' or 'submit'.
        execution_status (str):   Status from the last run/submit.
        compiler_output (str):    Stderr / compiler error text.
        runtime_output (str):     Stdout from the execution.
        stdin (str):              Input provided for the run.
        message (str):            Submission verdict message.
        expected_output (str):    Expected output (submissions only).
        actual_output (str):      Actual output (submissions only).

    Returns a single, consistent JSON schema regardless of status.
    The response shape is intentionally stable so that a future AI model
    can be swapped in without any frontend changes.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "error": "No data provided"}), 400

        # Delegate execution details classification and response building to AI Service
        response_payload = ai_service.get_mentor_feedback(data)

        return jsonify(response_payload)

    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "error": f"Mentor service error: {str(e)}"}), 500
