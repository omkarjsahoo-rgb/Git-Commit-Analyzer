import csv
import io
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from git import Actor, Repo

from app import create_app
from app.services import analytics_service, report_service

UTC = timezone.utc
AUTHOR = Actor("Test User", "test@example.com")
OTHER = Actor("Jane Doe", "jane@example.com")


def build_repo(path, items):
    """Throwaway repo. Each item is a message or a (message, Actor) pair, oldest first."""
    repo = Repo.init(path)
    for i, item in enumerate(items):
        message, actor = item if isinstance(item, tuple) else (item, AUTHOR)
        name = f"f{i}.txt"
        (Path(path) / name).write_text(message)
        repo.index.add([name])
        repo.index.commit(message, author=actor, committer=actor)
    repo.git.branch("-M", "main")
    repo.close()
    return str(path)


def read_csv(response):
    text = response.get_data(as_text=True)
    return list(csv.DictReader(io.StringIO(text.lstrip("\ufeff"))))


@pytest.fixture
def client(tmp_path):
    app = create_app({"DATABASE_PATH": tmp_path / "test.db", "TESTING": True})
    return app.test_client()


@pytest.fixture
def repo(tmp_path):
    # Newest first this reads: final commit, feat, Initial commit.
    return build_repo(tmp_path / "q", ["Initial commit", "feat: add login page", "final commit"])


# ---- CSV building ----

def test_to_csv_blocks_formula_injection_and_formats_values():
    text = report_service.to_csv(["a"], [["=SUM(1)"], ["+1"], ["-x"], ["@y"], ["safe"], [None], [True], [5]])
    assert text.startswith("\ufeff")
    rows = list(csv.reader(io.StringIO(text.lstrip("\ufeff"))))
    assert [r[0] for r in rows[1:]] == ["'=SUM(1)", "'+1", "'-x", "'@y", "safe", "", "yes", "5"]


def test_commits_csv_content(client, repo):
    response = client.get("/api/reports/commits.csv", query_string={"path": repo})
    assert response.status_code == 200
    rows = read_csv(response)
    assert len(rows) == 3
    by_subject = {r["subject"]: r for r in rows}

    bad = by_subject["final commit"]
    assert bad["score"] == "25"
    assert bad["rating"] == "poor"
    assert bad["conventional"] == "no"
    assert "vague" in bad["issues"]

    good = by_subject["feat: add login page"]
    assert good["score"] == "100"
    assert good["conventional"] == "yes"
    assert good["type"] == "feat"

    auto = by_subject["Initial commit"]
    assert auto["score"] == ""
    assert auto["rating"] == "exempt"
    assert auto["conventional"] == ""


def test_csv_download_headers(client, repo):
    response = client.get("/api/reports/commits.csv", query_string={"path": repo})
    assert response.mimetype == "text/csv"
    disposition = response.headers["Content-Disposition"]
    assert disposition.startswith('attachment; filename="q-commits-')
    assert disposition.endswith('.csv"')


def test_commits_csv_neutralizes_formulas(client, tmp_path):
    path = build_repo(tmp_path / "evil", ["=1+1 evil"])
    rows = read_csv(client.get("/api/reports/commits.csv", query_string={"path": path}))
    assert rows[0]["subject"] == "'=1+1 evil"


def test_contributors_csv(client, tmp_path):
    path = build_repo(tmp_path / "c", [
        ("feat: add a", AUTHOR),
        ("feat: add b", OTHER),
        ("fix: fix c", AUTHOR),
    ])
    rows = read_csv(client.get("/api/reports/contributors.csv", query_string={"path": path}))
    assert [r["name"] for r in rows] == ["Test User", "Jane Doe"]
    assert rows[0]["commits"] == "2"
    assert rows[1]["commits"] == "1"


def test_branches_csv(client, repo):
    git_repo = Repo(repo)
    git_repo.git.branch("feature/x")
    git_repo.close()

    rows = read_csv(client.get("/api/reports/branches.csv", query_string={"path": repo}))
    by_name = {r["name"]: r for r in rows}
    assert set(by_name) == {"main", "feature/x"}
    assert by_name["main"]["is_current"] == "yes"
    assert by_name["main"]["is_base"] == "yes"
    assert by_name["feature/x"]["status"] == "active"
    assert by_name["feature/x"]["flagged_inactive"] == "no"


def test_branches_csv_rejects_bad_threshold(client, repo):
    response = client.get("/api/reports/branches.csv", query_string={"path": repo, "inactive_days": "abc"})
    assert response.status_code == 400


# ---- health summary ----

def test_health_endpoint(client, repo):
    data = client.get("/api/reports/health", query_string={"path": repo}).get_json()

    # 70% of quality 62.5 plus 30% of hygiene 100 = 73.75
    assert data["health"]["score"] == pytest.approx(73.75, abs=0.1)
    assert data["health"]["grade"] == "attention"
    assert [c["weight"] for c in data["health"]["components"]] == [70, 30]

    metrics = data["metrics"]
    assert metrics["total_commits"] == 3
    assert metrics["contributor_count"] == 1
    assert metrics["average_quality"] == 62.5
    assert metrics["conventional_percent"] == 50.0
    assert metrics["vague_count"] == 1

    assert data["lowest_commits"][0]["subject"] == "final commit"
    assert data["lowest_commits"][0]["issues"]
    assert "vague" in [row["code"] for row in data["issue_breakdown"]]
    assert any("vague" in f["message"] for f in data["findings"])
    assert data["truncated"] is False
    assert data["repository"]["name"] == "q"


def test_health_for_empty_repository(client, tmp_path):
    Repo.init(tmp_path / "empty").close()
    data = client.get("/api/reports/health", query_string={"path": str(tmp_path / "empty")}).get_json()
    assert data["health"]["score"] is None
    assert data["health"]["grade"] == "unknown"
    assert data["metrics"]["total_commits"] == 0
    assert data["lowest_commits"] == []


def branch(name, days_old, now, current=False):
    return {
        "name": name,
        "is_current": current,
        "last_commit_hash": "abc1234",
        "last_commit_at": now - timedelta(days=days_old),
        "last_commit_author": "Alice",
        "unmerged_commits": 0,
    }


def test_health_summary_penalizes_flagged_branches():
    now = datetime(2026, 11, 9, 12, tzinfo=UTC)
    commits = report_service.analyze_commits([{
        "hash": "a" * 40,
        "short_hash": "aaaaaaa",
        "subject": "feat: add x",
        "message": "feat: add x",
        "author_name": "Alice",
        "author_email": "a@x.com",
        "authored_at": now - timedelta(days=1),
        "committed_at": now - timedelta(days=1),
        "is_merge": False,
    }])
    contributors = analytics_service.contributor_stats(commits)
    branches = analytics_service.analyze_branches(
        [branch("main", 1, now, current=True), branch("feature/new", 1, now), branch("old", 200, now)],
        "main", 30, now=now,
    )

    report = report_service.health_summary(commits, 1, contributors, branches, now=now)

    # Quality 100 and hygiene 50 (1 of 2 reviewable branches flagged): (70*100 + 30*50) / 100
    assert report["health"]["score"] == 85.0
    assert report["health"]["grade"] == "healthy"
    assert report["health"]["components"][1]["score"] == 50.0
    assert report["metrics"]["flagged_branches"] == 1
    assert report["metrics"]["days_since_last_commit"] == 1
    assert any(f["level"] == "warning" and "old" in f["message"] for f in report["findings"])


# ---- snapshots (analysis history) ----

def test_snapshots_save_and_list(client, repo):
    assert client.post("/api/reports/snapshots", json={"path": repo}).status_code == 201
    assert client.post("/api/reports/snapshots", json={"path": repo}).status_code == 201

    snapshots = client.get("/api/reports/snapshots", query_string={"path": repo}).get_json()["snapshots"]
    assert len(snapshots) == 2
    assert snapshots[0]["id"] > snapshots[1]["id"]  # newest first
    assert snapshots[0]["total_commits"] == 3
    assert snapshots[0]["contributor_count"] == 1
    assert snapshots[0]["branch_count"] == 1
    assert snapshots[0]["quality_score"] == 62.5


def test_snapshot_requires_path(client):
    assert client.post("/api/reports/snapshots", json={}).status_code == 400


def test_snapshots_are_kept_per_repository(client, repo, tmp_path):
    other = build_repo(tmp_path / "other", ["feat: add thing"])
    client.post("/api/reports/snapshots", json={"path": repo})
    result = client.get("/api/reports/snapshots", query_string={"path": other}).get_json()
    assert result["snapshots"] == []