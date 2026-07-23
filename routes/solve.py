from flask import Blueprint, render_template, request, redirect, session, jsonify
from services.ai_service import AIService

solve_bp = Blueprint("solve", __name__)


@solve_bp.route("/solve", methods=["GET", "POST"])
def solve():
    if "user_id" not in session:
        return redirect("/")

    if request.method == "POST":
        question  = request.form.get("question", "").strip()
        technique = request.form.get("technique", "").strip()
        language  = request.form.get("language", "Python").strip()

        if not question:
            return jsonify({"error": "Please enter a question."}), 400

        try:
            ai_service = AIService()
            json_data = ai_service.solve_problem(question, technique, language)
            
            # Assemble the structured JSON into Markdown for the existing frontend
            answer = f"### 1. Problem Classification\n{json_data.get('classification', '')}\n\n"
            answer += f"### 2. Key Observation\n{json_data.get('key_observation', '')}\n\n"
            answer += f"### 3. Algorithm / Approach\n{json_data.get('approach', '')}\n\n"
            answer += f"### 4. Time & Space Complexity\n\n"
            
            complexity = json_data.get('complexity', {})
            answer += f"| Metric | Complexity Analysis |\n"
            answer += f"| :--- | :--- |\n"
            answer += f"| ⏱️ **Time** | `{complexity.get('time', 'N/A')}` |\n"
            answer += f"| 💾 **Space** | `{complexity.get('space', 'N/A')}` |\n\n"
            
            answer += f"### 5. Implementation\n```{language.lower()}\n{json_data.get('implementation', '')}\n```\n\n"
            answer += f"### 6. Line-by-line Explanation\n{json_data.get('explanation', '')}\n"

            # Return both the parsed answer (for backward compatibility) and the raw JSON (for future usage)
            return jsonify({
                "answer": answer,
                "raw_data": json_data
            })

        except Exception as e:
            return jsonify({"error": f"AI service error: {str(e)}"}), 500

    return render_template("solve.html")
