from flask import Flask, flash, jsonify, redirect, render_template, request
from config import Config
from extensions import limiter, generate_csrf_token
from routes import register_blueprints


def create_app():
    """Application factory."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Validate critical config at startup
    if not app.secret_key:
        raise RuntimeError(
            "SECRET_KEY is not set. "
            "Add SECRET_KEY=your-secret-key to the .env file."
        )

    # Initialize rate limiter
    limiter.init_app(app)

    # Register all route blueprints
    register_blueprints(app)

    # Inject csrf_token into all templates for JS consumption
    @app.context_processor
    def inject_csrf_token():
        return dict(csrf_token=generate_csrf_token())

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Not found"}), 404
        return render_template("errors.html", code=404, message="Page not found"), 404

    @app.errorhandler(403)
    def forbidden(e):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Forbidden"}), 403
        return render_template("errors.html", code=403, message="Access denied"), 403

    @app.errorhandler(500)
    def server_error(e):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Internal server error"}), 500
        return render_template("errors.html", code=500, message="Something went wrong"), 500

    # Rate-limit exceeded handler
    @app.errorhandler(429)
    def ratelimit_handler(e):
        flash("Too many attempts. Please try again in a few minutes.", "error")
        return render_template("login.html", csrf_token=generate_csrf_token()), 429

    return app


app = create_app()


if __name__ == "__main__":
    app.run()