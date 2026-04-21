from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.questions import questions_bp
from routes.solve import solve_bp
from routes.problems import problems_bp
from routes.execute import execute_bp
from routes.collection import collection_bp


def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(questions_bp)
    app.register_blueprint(solve_bp)
    app.register_blueprint(problems_bp)
    app.register_blueprint(execute_bp)
    app.register_blueprint(collection_bp)
