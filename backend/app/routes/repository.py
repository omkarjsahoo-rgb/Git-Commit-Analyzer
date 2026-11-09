from flask import Blueprint, jsonify, request

from ..database import get_db
from ..services import git_service
from ..utils.validators import clean_repo_path

repository_bp = Blueprint("repository", __name__, url_prefix="/api/repository")


@repository_bp.post("/open")
def open_repository():
    """Validate a path, return summary info and remember the repository."""
    data = request.get_json(silent=True) or {}
    path = clean_repo_path(data.get("path"))

    with git_service.open_repository(path) as repo:
        info = git_service.get_repository_info(repo)

    with get_db() as db:
        db.execute(
            """
            INSERT INTO repositories (path, name) VALUES (?, ?)
            ON CONFLICT(path) DO UPDATE SET
                name = excluded.name,
                last_opened_at = CURRENT_TIMESTAMP
            """,
            (info["path"], info["name"]),
        )

    return jsonify({"valid": True, "repository": info})


@repository_bp.get("/recent")
def recent_repositories():
    with get_db() as db:
        rows = db.execute(
            """
            SELECT path, name, last_opened_at FROM repositories
            ORDER BY last_opened_at DESC, id DESC LIMIT 10
            """
        ).fetchall()
    return jsonify({"repositories": [dict(row) for row in rows]})