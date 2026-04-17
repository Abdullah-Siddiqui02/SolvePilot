"""
AI Solve route: generates structured coding solutions using the Groq API.
"""

from flask import Blueprint, render_template, request, redirect, session, jsonify
from extensions import groq_client

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

        # Build the prompt
        prompt = f"""You are an expert coding interview coach.

Question: {question}
{f"Technique/Approach to use: {technique}" if technique else ""}
Language: {language}

Please provide a complete, structured solution with the following sections:

1. **Approach** – Explain the high-level strategy in 2-3 sentences.
2. **Technique** – Explain why "{technique if technique else 'the chosen technique'}" works best here.
3. **Code** – Write clean, well-commented {language} code.
4. **Line-by-Line Explanation** – Go through each important line of code and explain what it does and why.
5. **Time & Space Complexity** – State the Big-O analysis.

Format your response using Markdown."""

        try:
            chat = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=4096,
            )
            answer = chat.choices[0].message.content
            return jsonify({"answer": answer})

        except Exception as e:
            return jsonify({"error": f"AI service error: {str(e)}"}), 500

    return render_template("solve.html")
