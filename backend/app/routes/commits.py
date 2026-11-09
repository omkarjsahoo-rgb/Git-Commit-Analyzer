from flask import Blueprint, current_app, jsonify, request

from ..services import git_service, quality_checker
from ..utils.errors import ValidationError
from ..utils.validators import clean_repo_path, parse_int

commits_bp = Blueprint("commits", __name__, url_prefix="/api/commits")

RATINGS = ("excellent", "good", "fair", "poor", "exempt")
MAX_SEARCH_LENGTH = 200


@commits_bp.get("")
def list_commits():
    path = clean_repo_path(request.args.get("path"))
    limit = parse_int(request.args.get("limit"), 100, 1, 500, "limit")
    offset = parse_int(request.args.get("offset"), 0, 0, 1_000_000, "offset")
    branch = request.args.get("branch") or None
    query = (request.args.get("q") or "").strip().lower()
    rating = request.args.get("rating") or None

    if len(query) > MAX_SEARCH_LENGTH:
        raise ValidationError(f"Search text is too long (max {MAX_SEARCH_LENGTH} characters).")
    if rating and rating not in RATINGS:
        raise ValidationError(f"rating must be one of: {', '.join(RATINGS)}.")

    if query or rating:
        result = _filtered_commits(path, branch, query, rating, limit, offset)
    else:
        with git_service.open_repository(path) as repo:
            result = git_service.get_commits(repo, limit, offset, branch)
        for commit in result["commits"]:
            commit["quality"] = quality_checker.analyze_message(commit["message"], commit["is_merge"])
        result["truncated"] = False

    return jsonify({**result, "limit": limit, "offset": offset})


def _filtered_commits(path, branch, query, rating, limit, offset):
    """Scan the newest commits (up to the safety cap), keep the matches, return one page."""
    cap = current_app.config["MAX_ANALYZED_COMMITS"]
    with git_service.open_repository(path) as repo:
        data = git_service.get_commit_messages(repo, branch, cap)

    matches = []
    for commit in data["commits"]:
        if query:
            text = f"{commit['message']}\n{commit['author_name']}".lower()
            if query not in text and not commit["hash"].startswith(query):
                continue
        quality = quality_checker.analyze_message(commit["message"], commit["is_merge"])
        if rating and quality["rating"] != rating:
            continue
        commit["quality"] = quality
        matches.append(commit)

    return {
        "total": len(matches),
        "commits": matches[offset:offset + limit],
        "truncated": data["total"] > len(data["commits"]),
    }