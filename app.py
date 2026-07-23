import os
from flask import Flask, flash, redirect, render_template
from config import Config
from extensions import limiter
from routes import register_blueprints
from routes.auth import generate_csrf_token


def create_app():
    """Application factory."""
    app = Flask(__name__)
    app.secret_key = Config.SECRET_KEY

    # Initialize rate limiter
    limiter.init_app(app)

    # Register all route blueprints
    register_blueprints(app)

    # Rate-limit exceeded handler
    @app.errorhandler(429)
    def ratelimit_handler(e):
        flash("Too many attempts. Please try again in a few minutes.", "error")
        return render_template("login.html", csrf_token=generate_csrf_token()), 429

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_ENV") == "development")