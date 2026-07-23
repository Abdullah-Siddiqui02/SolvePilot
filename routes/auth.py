import secrets
from flask import Blueprint, render_template, request, redirect, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import get_db, limiter

auth_bp = Blueprint("auth", __name__)


def generate_csrf_token():
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_hex(32)
    return session["_csrf_token"]

def validate_csrf_token(token):
    stored = session.get("_csrf_token")
    if not stored or not secrets.compare_digest(stored, token):
        return False
    return True

#  Login 

@auth_bp.route("/", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def login():
    if request.method == "POST":
        if not validate_csrf_token(request.form.get("csrf_token", "")):
            flash("Session expired. Please try again.", "error")
            return redirect("/")

        username = request.form["username"]
        password = request.form["password"]

        db, cursor = get_db()
        try:
            cursor.execute(
                "SELECT id, password FROM users WHERE username=%s",
                (username,),
            )
            user = cursor.fetchone()

            if user and check_password_hash(user[1], password):
                session["user_id"] = user[0]
                return redirect("/dashboard")
            else:
                flash("Invalid username or password.", "error")
        finally:
            cursor.close()
            db.close()

    return render_template("login.html", csrf_token=generate_csrf_token())


# Signup 

@auth_bp.route("/signup", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def signup():
    if request.method == "POST":
        if not validate_csrf_token(request.form.get("csrf_token", "")):
            flash("Session expired. Please try again.", "error")
            return redirect("/signup")

        username = request.form["username"]
        password = request.form["password"]
        confirm  = request.form["confirm_password"]

        # Basic validation
        if not username or not password:
            flash("All fields are required.", "error")
            return redirect("/signup")

        if len(password) < 8:
            flash("Password must be at least 8 characters long.", "error")
            return redirect("/signup")

        if password != confirm:
            flash("Passwords do not match.", "error")
            return redirect("/signup")

        db, cursor = get_db()
        try:
            cursor.execute("SELECT id FROM users WHERE username=%s", (username,))
            if cursor.fetchone():
                flash("Username already exists.", "error")
                return redirect("/signup")

            # Insert new user with hashed password
            hashed_pw = generate_password_hash(password)
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s)",
                (username, hashed_pw),
            )
            db.commit()
        finally:
            cursor.close()
            db.close()

        flash("Account created! Please log in.", "success")
        return redirect("/")

    return render_template("signup.html", csrf_token=generate_csrf_token())


# Logout 

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/")
