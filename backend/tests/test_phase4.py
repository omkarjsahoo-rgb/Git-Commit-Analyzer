from datetime import datetime, timezone
from pathlib import Path

import pytest
from git import Actor, Repo

from app import create_app
from app.services import analytics_service as an

UTC = timezone.utc
ALICE = Actor("Alice", "a@x.com")
ALICE_ALT = Actor("Alice B", "A@X.COM")  # same person, different spelling
BOB = Actor("Bob", "b@x.com")


def dt(month, day, hour=12, year=2026):
    return datetime(year, month, day, hour, tzinfo=UTC)


def rec(name, email, when, message="feat: add thing", merge=False):
    return {
        "author_name": name,
        "author_email": email,
        "authored_at": when,
        "message": message,
        "is_merge": merge,
    }


def build_repo(path, commits):
    """Throwaway repo. Each item is a message or a (message, Actor) pair, oldest first."""
    repo = Repo.init(path)
    for i, item in enumerate(commits):
        message, actor = item if isinstance(item, tuple) else (item, ALICE)
        name = f"f{i}.txt"
        (Path(path) / name).write_text(message)
        repo.index.add([name])
        repo.index.commit(message, author=actor, committer=actor)
    repo.git.branch("-M", "main")
    repo.close()
    return str(path)


@pytest.fixture
def client(tmp_path):
    app = create_app({"DATABASE_PATH": tmp_path / "test.db", "TESTING": True})
    return app.test_client()


# ---- contributors ----

def test_contributors_group_by_email_ignoring_case():
    records = [  # newest first, like Git returns them
        rec("Bob", "b@x.com", dt(11, 9)),
        rec("Alice", "a@x.com", dt(11, 8)),
        rec("Alice B", "A@X.COM", dt(11, 7)),
        rec("Alice", "a@x.com", dt(11, 1)),
    ]
    result = an.contributor_stats(records)
    assert result["total_commits"] == 4
    assert result["contributor_count"] == 2
    top = result["contributors"][0]
    assert top["name"] == "Alice"
    assert top["email"] == "a@x.com"
    assert top["commits"] == 3
    assert top["percent"] == 75.0
    assert top["active_days"] == 3
    assert top["first_commit_at"] == dt(11, 1).isoformat()
    assert top["last_commit_at"] == dt(11, 8).isoformat()
    assert result["contributors"][1]["name"] == "Bob"


def test_contributor_quality_skips_exempt_commits():
    records = [
        rec("Alice", "a@x.com", dt(11, 3), "feat: add login page"),
        rec("Alice", "a@x.com", dt(11, 2), "final commit"),
        rec("Alice", "a@x.com", dt(11, 1), "Merge remote changes", merge=True),
    ]
    alice = an.contributor_stats(records)["contributors"][0]
    assert alice["commits"] == 3
    assert alice["merge_commits"] == 1
    assert alice["scored_commits"] == 2
    assert alice["average_quality"] == 62.5


def test_contributors_empty():
    result = an.contributor_stats([])
    assert result == {"total_commits": 0, "contributor_count": 0, "contributors": []}


# ---- activity ----

def test_activity_daily_fills_gaps():
    records = [rec("A", "a@x.com", dt(11, 11)), rec("A", "a@x.com", dt(11, 9, 8)), rec("B", "b@x.com", dt(11, 9, 20))]
    result = an.activity_series(records, "daily")
    assert result["labels"] == ["2026-11-09", "2026-11-10", "2026-11-11"]
    assert result["commits"] == [2, 0, 1]
    assert result["active_contributors"] == [2, 0, 1]
    assert result["busiest"] == {"label": "2026-11-09", "commits": 2}


def test_activity_weekly_groups_by_monday():
    # 2026-11-09 is a Monday, so Sunday the 8th belongs to the week starting the 2nd.
    records = [rec("A", "a@x.com", dt(11, 11)), rec("A", "a@x.com", dt(11, 8))]
    result = an.activity_series(records, "weekly")
    assert result["labels"] == ["2026-11-02", "2026-11-09"]
    assert result["commits"] == [1, 1]


def test_activity_monthly_fills_gaps():
    records = [rec("A", "a@x.com", dt(11, 1)), rec("A", "a@x.com", dt(9, 30))]
    result = an.activity_series(records, "monthly")
    assert result["labels"] == ["2026-09", "2026-10", "2026-11"]
    assert result["commits"] == [1, 0, 1]


def test_activity_periods_limit_reports_outside_range():
    records = [rec("A", "a@x.com", dt(11, 9)), rec("A", "a@x.com", dt(11, 1))]
    result = an.activity_series(records, "daily", periods=3)
    assert result["labels"] == ["2026-11-07", "2026-11-08", "2026-11-09"]
    assert result["commits"] == [0, 0, 1]
    assert result["commits_in_range"] == 1
    assert result["commits_outside_range"] == 1


def test_activity_empty():
    result = an.activity_series([], "weekly")
    assert result["labels"] == []
    assert result["busiest"] is None


def test_activity_unknown_period_rejected():
    with pytest.raises(ValueError):
        an.activity_series([], "yearly")


# ---- branches ----

def branch(name, days_old, now, current=False):
    from datetime import timedelta
    return {
        "name": name,
        "is_current": current,
        "last_commit_hash": "abc1234",
        "last_commit_at": now - timedelta(days=days_old),
        "last_commit_author": "Alice",
        "unmerged_commits": 0,
    }


def test_branch_statuses_and_summary():
    now = dt(11, 9)
    branches = [
        branch("main", 1, now, current=True),
        branch("feature/new", 5, now),
        branch("feature/mid", 45, now),
        branch("feature/old", 100, now),
    ]
    result = an.analyze_branches(branches, "main", inactive_days=30, now=now)
    by_name = {b["name"]: b for b in result["branches"]}
    assert by_name["feature/new"]["status"] == "active"
    assert by_name["feature/mid"]["status"] == "stale"
    assert by_name["feature/mid"]["flagged_inactive"] is False
    assert by_name["feature/old"]["status"] == "inactive"
    assert by_name["feature/old"]["flagged_inactive"] is True
    assert by_name["feature/old"]["days_since_last_commit"] == 100
    assert result["summary"] == {"total": 4, "active": 2, "stale": 1, "inactive": 1, "flagged_inactive": 1}
    assert [b["name"] for b in result["branches"]][0] == "main"  # newest first


def test_protected_branches_are_never_flagged():
    now = dt(11, 9)
    branches = [branch("main", 200, now), branch("develop", 200, now), branch("topic", 200, now, current=True)]
    result = an.analyze_branches(branches, "main", inactive_days=30, now=now)
    assert all(b["status"] == "inactive" for b in result["branches"])
    assert result["summary"]["flagged_inactive"] == 0
    assert all(b["protected"] for b in result["branches"])


# ---- API ----

def test_contributors_endpoint(client, tmp_path):
    path = build_repo(tmp_path / "c", [
        ("feat: add a", ALICE),
        ("feat: add b", ALICE_ALT),
        ("fix: fix c", ALICE),
        ("feat: add d", BOB),
    ])
    data = client.get("/api/contributors", query_string={"path": path}).get_json()
    assert data["contributor_count"] == 2
    assert data["analyzed"] == 4
    assert data["truncated"] is False
    assert data["contributors"][0]["name"] == "Alice"
    assert data["contributors"][0]["commits"] == 3


def test_contributors_empty_repo(client, tmp_path):
    Repo.init(tmp_path / "empty").close()
    data = client.get("/api/contributors", query_string={"path": str(tmp_path / "empty")}).get_json()
    assert data["contributor_count"] == 0
    assert data["contributors"] == []


def test_activity_endpoint(client, tmp_path):
    path = build_repo(tmp_path / "a", ["feat: add a", "feat: add b"])
    for period in ("daily", "weekly", "monthly"):
        data = client.get("/api/activity", query_string={"path": path, "period": period}).get_json()
        assert data["period"] == period
        assert data["total_commits"] == 2
        assert sum(data["commits"]) == 2
        assert len(data["labels"]) == len(data["commits"])


def test_activity_rejects_bad_period(client, tmp_path):
    path = build_repo(tmp_path / "a", ["feat: add a"])
    response = client.get("/api/activity", query_string={"path": path, "period": "yearly"})
    assert response.status_code == 400


def test_activity_rejects_bad_periods_value(client, tmp_path):
    path = build_repo(tmp_path / "a", ["feat: add a"])
    response = client.get("/api/activity", query_string={"path": path, "periods": 0})
    assert response.status_code == 400


def test_branch_analysis_endpoint(client, tmp_path):
    path = build_repo(tmp_path / "b", ["feat: add one"])
    repo = Repo(path)
    repo.git.branch("feature/x")
    repo.close()

    data = client.get("/api/branches/analysis", query_string={"path": path}).get_json()
    assert data["base_branch"] == "main"
    assert data["summary"]["total"] == 2
    assert data["summary"]["flagged_inactive"] == 0
    assert all(b["status"] == "active" for b in data["branches"])


def test_branch_analysis_rejects_bad_threshold(client, tmp_path):
    path = build_repo(tmp_path / "b", ["feat: add one"])
    response = client.get("/api/branches/analysis", query_string={"path": path, "inactive_days": "abc"})
    assert response.status_code == 400


def test_unmerged_commits_are_counted(client, tmp_path):
    path = build_repo(tmp_path / "u", ["feat: add one"])
    repo = Repo(path)
    repo.git.checkout("-b", "feature/y")
    (Path(path) / "extra.txt").write_text("x")
    repo.index.add(["extra.txt"])
    repo.index.commit("feat: add extra", author=ALICE, committer=ALICE)
    repo.git.checkout("main")
    repo.close()

    data = client.get("/api/branches/analysis", query_string={"path": path}).get_json()
    by_name = {b["name"]: b for b in data["branches"]}
    assert by_name["feature/y"]["unmerged_commits"] == 1
    assert by_name["main"]["unmerged_commits"] == 0


def test_phase4_endpoints_are_read_only(client, tmp_path):
    path = build_repo(tmp_path / "r", ["feat: add one", "fix: fix two"])
    repo = Repo(path)
    repo.git.branch("feature/x")
    before = {h.name: h.commit.hexsha for h in repo.heads}

    client.get("/api/contributors", query_string={"path": path})
    client.get("/api/activity", query_string={"path": path})
    client.get("/api/branches/analysis", query_string={"path": path})

    after = {h.name: h.commit.hexsha for h in repo.heads}
    assert before == after
    assert repo.git.status("--porcelain") == ""
    repo.close()