from flask import Blueprint, jsonify, request

from ..services import analytics_service, git_service
from ..utils.validators import clean_repo_path, parse_int

branches_bp = Blueprint("branches", __name__, url_prefix="/api/branches")


@branches_bp.get("")
def list_branches():
    path = clean_repo_path(request.args.get("path"))

    with git_service.open_repository(path) as repo:
        branches = git_service.get_branches(repo)

    return jsonify({"branches": branches})


@branches_bp.get("/analysis")
def analyze_branches():
    """Label branches as active / stale / inactive. Read-only: nothing is ever deleted."""
    path = clean_repo_path(request.args.get("path"))
    inactive_days = parse_int(request.args.get("inactive_days"), 30, 1, 3650, "inactive_days")

    with git_service.open_repository(path) as repo:
        details = git_service.get_branch_details(repo)

    return jsonify(
        analytics_service.analyze_branches(details["branches"], details["base_branch"], inactive_days)
    )