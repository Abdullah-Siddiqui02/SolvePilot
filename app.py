from flask import Flask, render_template, request, redirect, session
import mysql.connector

app = Flask(__name__)
app.secret_key = "secret123"

# Database connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Abdullah@#",
    database="interview_prep"
)

cursor = db.cursor(buffered=True)

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        cursor.execute(
            "SELECT * FROM users WHERE username=%s AND password=%s",
            (username, password)
        )
        user = cursor.fetchone()

        if user:
            session["user_id"] = user[0]
            return redirect("/dashboard")
        else:
            return "Invalid login"

    return render_template("login.html")


# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/")

    user_id = session["user_id"]

    cursor.execute(
        "SELECT COUNT(*) FROM questions WHERE user_id=%s",
        (user_id,)
    )
    total = cursor.fetchone()[0]

    cursor.execute(
        "SELECT topic, COUNT(*) FROM questions WHERE user_id=%s GROUP BY topic",
        (user_id,)
    )
    topics = cursor.fetchall()

    return render_template("dashboard.html", total=total, topics=topics)


# ---------------- ADD QUESTION ----------------
@app.route("/add", methods=["GET", "POST"])
def add():
    if "user_id" not in session:
        return redirect("/")

    if request.method == "POST":
        title = request.form["title"]
        topic = request.form["topic"]
        difficulty = request.form["difficulty"]
        user_id = session["user_id"]

        cursor.execute(
            "INSERT INTO questions (user_id, title, topic, difficulty) VALUES (%s, %s, %s, %s)",
            (user_id, title, topic, difficulty)
        )
        db.commit()

        return redirect("/dashboard")

    return render_template("add_question.html")


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)