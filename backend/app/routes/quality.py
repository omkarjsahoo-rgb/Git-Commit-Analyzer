from flask import Blueprint, current_app, jsonify, request

from ..services import git_service, quality_checker
from ..utils.errors import ValidationError
from ..utils.validators import clean_repo_path

quality_bp = Blueprint("quality", __name__, url_prefix="/api/quality")

MAX_MESSAGE_LENGTH = 5000


@quality_bp.post("/check")
def check_message():
    """Score a message typed by the user. No repository needed."""
    data = request.get_json(silent=True) or {}
    message = data.get("message")
    if not isinstance(message, str) or not message.strip():
        raise ValidationError("A commit message is required.")
    if len(message) > MAX_MESSAGE_LENGTH:
        raise ValidationError(f"Message is too long (max {MAX_MESSAGE_LENGTH} characters).")
    return jsonify(quality_checker.analyze_message(message))


@quality_bp.get("/summary")
def quality_summary():
    """Quality numbers for a whole repository."""
    path = clean_repo_path(request.args.get("path"))
    branch = request.args.get("branch") or None
    limit = current_app.config["MAX_ANALYZED_COMMITS"]

    with git_service.open_repository(path) as repo:
        data = git_service.get_commit_messages(repo, branch, limit)

    commits = data["commits"]
    for commit in commits:
        commit["analysis"] = quality_checker.analyze_message(commit["message"], commit["is_merge"])

    scored = [c for c in commits if not c["analysis"]["exempt"]]
    lowest = sorted(scored, key=lambda c: c["analysis"]["score"])[:5]

    return jsonify({
        "summary": quality_checker.summarize([c["analysis"] for c in commits]),
        "analyzed": len(commits),
        "total": data["total"],
        "truncated": data["total"] > len(commits),
        "lowest_scoring": [
            {
                "short_hash": c["short_hash"],
                "subject": c["subject"],
                "author_name": c["author_name"],
                "score": c["analysis"]["score"],
                "rating": c["analysis"]["rating"],
            }
            for c in lowest
        ],
    })