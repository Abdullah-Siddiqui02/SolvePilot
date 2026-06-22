from flask import Blueprint, jsonify, request, session
from extensions import get_db, groq_client
import json
import traceback

ai_bp = Blueprint("ai", __name__)

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

        # 2. Build system instructions
        system_instructions = f"""You are 'SolvePilot AI', an expert coding mentor. Your goal is to help students learn and improve.

CAPABILITIES:
- Provide HINTS and EXPLANATIONS for logic issues.
- Provide LINE-BY-LINE EXPLANATIONS of code if requested.
- Suggest BETTER/OPTIMIZED SOLUTIONS if the student asks for improvements.
- Identify syntax or logical errors clearly.

CONTEXT:
Problem Title: {problem_title}
Problem Description: {problem_desc}

GUIDELINES:
- Be encouraging and helpful.
- DO NOT just give the full solution immediately unless they are very stuck; prioritize teaching.
- Use Markdown for code snippets and formatting.
- Keep responses focused and readable.
"""

        user_content = f"""STUDENT'S CURRENT CODE ({language}):
```
{code}
```

STUDENT'S QUESTION:
{user_query}"""

        # 3. Build messages array for Groq
        messages = [{"role": "system", "content": system_instructions}]
        
        # Add historical messages (max last 10 to keep context window clean)
        for msg in chat_history[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
            
        # Add current user message
        messages.append({"role": "user", "content": user_content})


        # 3. Call Groq
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )

        
        ai_response = completion.choices[0].message.content
        
        return jsonify({
            "response": ai_response
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"System error: {str(e)}"}), 500
