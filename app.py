from flask import Flask
from config import Config
from routes import register_blueprints


def create_app():
    """Application factory."""
    app = Flask(__name__)
    app.secret_key = Config.SECRET_KEY

    # Register all route blueprints
    register_blueprints(app)
    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)