from urllib.parse import urlsplit

from flask import Flask, jsonify, request
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

    from .routes.analytics import analytics_bp
    from .routes.branches import branches_bp
    from .routes.commits import commits_bp
    from .routes.quality import quality_bp
    from .routes.reports import reports_bp
    from .routes.repository import repository_bp

    app.register_blueprint(repository_bp)
    app.register_blueprint(commits_bp)
    app.register_blueprint(branches_bp)
    app.register_blueprint(quality_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(reports_bp)

    @app.before_request
    def reject_unexpected_hosts():
        # Only answer requests addressed to this computer. A malicious website can point its
        # own domain name at 127.0.0.1 to reach local servers; its requests carry that domain
        # in the Host header, so refusing unknown hosts stops it.
        hostname = urlsplit(f"//{request.host}").hostname
        if hostname not in app.config["ALLOWED_HOSTS"]:
            return jsonify({"error": "This server only answers requests addressed to localhost."}), 403

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    @app.errorhandler(AppError)
    def handle_app_error(err):
        return jsonify({"error": err.message}), err.status_code

    @app.errorhandler(GitCommandError)
    def handle_git_error(err):
        app.logger.warning("Git command failed: %s", err)
        details = f"{err} {getattr(err, 'stderr', '')}".lower()
        if "dubious ownership" in details:
            message = (
                "Git refuses to read this folder because it belongs to a different user. "
                'Run: git config --global --add safe.directory "<path to the folder>" '
                "and then open it again."
            )
            return jsonify({"error": message}), 422
        return jsonify({"error": "Git could not read this repository. See the backend terminal for details."}), 422

    @app.errorhandler(HTTPException)
    def handle_http_error(err):
        return jsonify({"error": err.description}), err.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(err):
        app.logger.exception("Unexpected error")
        return jsonify({"error": "Unexpected server error. Check the backend terminal for details."}), 500

    return app