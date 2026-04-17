from flask import Flask, render_template, request, redirect, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

# ──────────────────────────────────────────────
#  Groq AI Client
# ──────────────────────────────────────────────
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ──────────────────────────────────────────────
#  Database Connection
# ──────────────────────────────────────────────
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Abdullah@#",
    database="interview_prep1"
)
cursor = db.cursor(buffered=True)


# ──────────────────────────────────────────────
#  AUTH – Login
# ──────────────────────────────────────────────
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        cursor.execute(
            "SELECT id, password FROM users WHERE username=%s",
            (username,)
        )
        user = cursor.fetchone()

        if user and check_password_hash(user[1], password):
            session["user_id"] = user[0]
            return redirect("/dashboard")
        else:
            flash("Invalid username or password.", "error")

    return render_template("login.html")


# ──────────────────────────────────────────────
#  AUTH – Signup
# ──────────────────────────────────────────────
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        confirm  = request.form["confirm_password"]

        # Basic validation
        if not username or not password:
            flash("All fields are required.", "error")
            return redirect("/signup")

        if password != confirm:
            flash("Passwords do not match.", "error")
            return redirect("/signup")

        # Check if user already exists
        cursor.execute("SELECT id FROM users WHERE username=%s", (username,))
        if cursor.fetchone():
            flash("Username already exists.", "error")
            return redirect("/signup")

        # Insert new user with hashed password
        hashed_pw = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (%s, %s)",
            (username, hashed_pw)
        )
        db.commit()

        flash("Account created! Please log in.", "success")
        return redirect("/")

    return render_template("signup.html")


# ──────────────────────────────────────────────
#  DASHBOARD
# ──────────────────────────────────────────────
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/")

    user_id = session["user_id"]

    # Total questions
    cursor.execute(
        "SELECT COUNT(*) FROM questions WHERE user_id=%s",
        (user_id,)
    )
    total = cursor.fetchone()[0]

    # Questions grouped by topic
    cursor.execute(
        "SELECT topic, COUNT(*) FROM questions WHERE user_id=%s GROUP BY topic",
        (user_id,)
    )
    topics = cursor.fetchall()

    # Questions grouped by difficulty
    cursor.execute(
        "SELECT difficulty, COUNT(*) FROM questions WHERE user_id=%s GROUP BY difficulty",
        (user_id,)
    )
    difficulties = cursor.fetchall()

    return render_template(
        "dashboard.html",
        total=total,
        topics=topics,
        difficulties=difficulties
    )


# ──────────────────────────────────────────────
#  ADD QUESTION
# ──────────────────────────────────────────────
@app.route("/add", methods=["GET", "POST"])
def add():
    if "user_id" not in session:
        return redirect("/")

    if request.method == "POST":
        title      = request.form["title"]
        topic      = request.form["topic"]
        difficulty = request.form["difficulty"]
        user_id    = session["user_id"]

        cursor.execute(
            "INSERT INTO questions (user_id, title, topic, difficulty) VALUES (%s, %s, %s, %s)",
            (user_id, title, topic, difficulty)
        )
        db.commit()

        flash("Question added successfully!", "success")
        return redirect("/dashboard")

    return render_template("add_question.html")


# ──────────────────────────────────────────────
#  AI SOLVE – Groq Powered
# ──────────────────────────────────────────────
@app.route("/solve", methods=["GET", "POST"])
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
                max_tokens=4096
            )
            answer = chat.choices[0].message.content
            return jsonify({"answer": answer})

        except Exception as e:
            return jsonify({"error": f"AI service error: {str(e)}"}), 500

    return render_template("solve.html")


# ──────────────────────────────────────────────
#  LOGOUT
# ──────────────────────────────────────────────
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ──────────────────────────────────────────────
#  Run
# ──────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True)