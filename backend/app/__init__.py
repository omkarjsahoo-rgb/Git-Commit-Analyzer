from flask import Flask, jsonify
from flask_cors import CORS
from git.exc import GitCommandError
from werkzeug.exceptions import HTTPException

from .config import Config
from .database import init_db
from .utils.errors import AppError


def create_app(config_overrides=None):
    """App factory: builds a configured Flask app (tests can pass overrides)."""
    app = Flask(__name__)
    app.config.from_object(Config)
    if config_overrides:
        app.config.update(config_overrides)

    CORS(app, origins=app.config["CORS_ORIGINS"])
    init_db(app)

    from .routes.branches import branches_bp
    from .routes.commits import commits_bp
    from .routes.repository import repository_bp
    from .routes.quality import quality_bp
    from .routes.analytics import analytics_bp
    from .routes.reports import reports_bp

    app.register_blueprint(repository_bp)
    app.register_blueprint(commits_bp)
    app.register_blueprint(branches_bp)
    app.register_blueprint(quality_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(reports_bp)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    @app.errorhandler(AppError)
    def handle_app_error(err):
        return jsonify({"error": err.message}), err.status_code

    @app.errorhandler(GitCommandError)
    def handle_git_error(err):
        app.logger.warning("Git command failed: %s", err)
        return jsonify({"error": "Git could not read this repository. See the backend terminal for details."}), 422

    @app.errorhandler(HTTPException)
    def handle_http_error(err):
        return jsonify({"error": err.description}), err.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(err):
        app.logger.exception("Unexpected error")
        return jsonify({"error": "Unexpected server error. Check the backend terminal for details."}), 500

    return app