from flask import Blueprint, jsonify, request

from ..services import git_service, quality_checker
from ..utils.validators import clean_repo_path, parse_int

commits_bp = Blueprint("commits", __name__, url_prefix="/api/commits")


@commits_bp.get("")
def list_commits():
    path = clean_repo_path(request.args.get("path"))
    limit = parse_int(request.args.get("limit"), 100, 1, 500, "limit")
    offset = parse_int(request.args.get("offset"), 0, 0, 1_000_000, "offset")
    branch = request.args.get("branch") or None

    with git_service.open_repository(path) as repo:
        result = git_service.get_commits(repo, limit, offset, branch)

    for commit in result["commits"]:
        commit["quality"] = quality_checker.analyze_message(commit["message"], commit["is_merge"])

    return jsonify({**result, "limit": limit, "offset": offset})