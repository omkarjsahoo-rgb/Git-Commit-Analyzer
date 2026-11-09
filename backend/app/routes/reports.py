import re
from datetime import datetime

from flask import Blueprint, Response, current_app, jsonify, request

from ..database import get_db, upsert_repository
from ..services import analytics_service, git_service, report_service
from ..utils.validators import clean_repo_path, parse_int

reports_bp = Blueprint("reports", __name__, url_prefix="/api/reports")


def _load(path, branch=None):
    """Read repository info, analyzed commits and branch details in one pass."""
    cap = current_app.config["MAX_ANALYZED_COMMITS"]
    with git_service.open_repository(path) as repo:
        info = git_service.get_repository_info(repo)
        data = git_service.get_commit_details(repo, branch, cap)
        branch_data = git_service.get_branch_details(repo)
    commits = report_service.analyze_commits(data["commits"])
    return info, commits, data["total"], branch_data


def _health_report(info, commits, total, branch_data, inactive_days=30):
    contributors = analytics_service.contributor_stats(commits)
    branches = analytics_service.analyze_branches(
        branch_data["branches"], branch_data["base_branch"], inactive_days
    )
    report = report_service.health_summary(commits, total, contributors, branches)
    report["repository"] = {"name": info["name"], "path": info["path"]}
    report["analyzed"] = len(commits)
    report["truncated"] = total > len(commits)
    return report, contributors


def _csv_response(info, kind, text):
    # Only safe characters in the file name, so it can never break the header.
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", info["name"]) or "repository"
    filename = f"{name}-{kind}-{datetime.now().strftime('%Y-%m-%d')}.csv"
    return Response(
        text,
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@reports_bp.get("/health")
def health():
    path = clean_repo_path(request.args.get("path"))
    info, commits, total, branch_data = _load(path)
    report, _ = _health_report(info, commits, total, branch_data)
    return jsonify(report)


@reports_bp.get("/commits.csv")
def commits_csv():
    path = clean_repo_path(request.args.get("path"))
    branch = request.args.get("branch") or None
    info, commits, _, _ = _load(path, branch)
    return _csv_response(info, "commits", report_service.commits_csv(commits))


@reports_bp.get("/contributors.csv")
def contributors_csv():
    path = clean_repo_path(request.args.get("path"))
    info, commits, _, _ = _load(path)
    people = analytics_service.contributor_stats(commits)["contributors"]
    return _csv_response(info, "contributors", report_service.contributors_csv(people))


@reports_bp.get("/branches.csv")
def branches_csv():
    path = clean_repo_path(request.args.get("path"))
    inactive_days = parse_int(request.args.get("inactive_days"), 30, 1, 3650, "inactive_days")
    with git_service.open_repository(path) as repo:
        info = git_service.get_repository_info(repo)
        details = git_service.get_branch_details(repo)
    analysis = analytics_service.analyze_branches(details["branches"], details["base_branch"], inactive_days)
    return _csv_response(info, "branches", report_service.branches_csv(analysis["branches"]))


@reports_bp.post("/snapshots")
def save_snapshot():
    """Store today's totals in this tool's own database. The analyzed repository is untouched."""
    data = request.get_json(silent=True) or {}
    path = clean_repo_path(data.get("path"))
    info, commits, total, branch_data = _load(path)
    report, contributors = _health_report(info, commits, total, branch_data)

    with get_db() as db:
        repository_id = upsert_repository(db, info["path"], info["name"])
        db.execute(
            """
            INSERT INTO analysis_history
                (repository_id, total_commits, contributor_count, branch_count, quality_score)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                repository_id,
                total,
                contributors["contributor_count"],
                info["branch_count"],
                report["metrics"]["average_quality"],
            ),
        )
    return jsonify({"saved": True}), 201


@reports_bp.get("/snapshots")
def list_snapshots():
    path = clean_repo_path(request.args.get("path"))
    with git_service.open_repository(path) as repo:
        info = git_service.get_repository_info(repo)

    with get_db() as db:
        rows = db.execute(
            """
            SELECT h.id, h.analyzed_at, h.total_commits, h.contributor_count,
                   h.branch_count, h.quality_score
            FROM analysis_history h
            JOIN repositories r ON r.id = h.repository_id
            WHERE r.path = ?
            ORDER BY h.id DESC
            LIMIT 20
            """,
            (info["path"],),
        ).fetchall()
    return jsonify({"snapshots": [dict(row) for row in rows]})