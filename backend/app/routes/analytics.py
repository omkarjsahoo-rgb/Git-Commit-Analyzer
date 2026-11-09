from flask import Blueprint, current_app, jsonify, request

from ..services import analytics_service, git_service
from ..utils.errors import ValidationError
from ..utils.validators import clean_repo_path, parse_int

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api")


def _read_records(path, branch):
    limit = current_app.config["MAX_ANALYZED_COMMITS"]
    with git_service.open_repository(path) as repo:
        data = git_service.get_commit_records(repo, branch, limit)
    return data["commits"], data["total"]


@analytics_bp.get("/contributors")
def contributors():
    path = clean_repo_path(request.args.get("path"))
    branch = request.args.get("branch") or None

    records, total = _read_records(path, branch)
    result = analytics_service.contributor_stats(records)
    return jsonify({
        **result,
        "analyzed": len(records),
        "truncated": total > len(records),
    })


@analytics_bp.get("/activity")
def activity():
    path = clean_repo_path(request.args.get("path"))
    branch = request.args.get("branch") or None
    period = request.args.get("period", "daily")
    if period not in analytics_service.PERIODS:
        raise ValidationError("period must be daily, weekly or monthly.")
    periods = parse_int(
        request.args.get("periods"), analytics_service.DEFAULT_PERIODS[period], 1, 1000, "periods"
    )

    records, total = _read_records(path, branch)
    result = analytics_service.activity_series(records, period, periods)
    return jsonify({
        **result,
        "analyzed": len(records),
        "truncated": total > len(records),
    })