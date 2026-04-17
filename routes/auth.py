from flask import Blueprint, render_template, request, redirect, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db, cursor

auth_bp = Blueprint("auth", __name__)


#  Login 

@auth_bp.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

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

    return render_template("login.html")


# Signup 

@auth_bp.route("/signup", methods=["GET", "POST"])
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

        flash("Account created! Please log in.", "success")
        return redirect("/")

    return render_template("signup.html")


# Logout 

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/")
