from pathlib import Path

import pytest
from git import Actor, Repo

from app import create_app
from app.services import quality_checker as qc

AUTHOR = Actor("Test User", "test@example.com")


def codes(result):
    return [issue["code"] for issue in result["issues"]]


def build_repo(path, messages):
    """Create a throwaway repo with one commit per message (oldest first)."""
    repo = Repo.init(path)
    for i, message in enumerate(messages):
        name = f"f{i}.txt"
        (Path(path) / name).write_text(message)
        repo.index.add([name])
        repo.index.commit(message, author=AUTHOR, committer=AUTHOR)
    repo.git.branch("-M", "main")
    repo.close()
    return str(path)


@pytest.fixture
def client(tmp_path):
    app = create_app({"DATABASE_PATH": tmp_path / "test.db", "TESTING": True})
    return app.test_client()


# ---- scoring ----

def test_conventional_message_scores_100():
    result = qc.analyze_message("feat(auth): add login endpoint")
    assert result["score"] == 100
    assert result["rating"] == "excellent"
    assert result["is_conventional"] is True
    assert result["type"] == "feat"
    assert result["scope"] == "auth"
    assert result["issues"] == []
    assert result["suggestions"] == []


def test_breaking_change_marker():
    result = qc.analyze_message("feat(api)!: drop v1 endpoints")
    assert result["is_conventional"] is True
    assert result["breaking"] is True


def test_plain_clear_message_is_good_but_flagged():
    result = qc.analyze_message("Add user login endpoint")
    assert result["score"] == 60
    assert result["rating"] == "good"
    assert result["is_conventional"] is False
    assert "not_conventional" in codes(result)
    assert result["suggested_subject"] == "feat: add user login endpoint"


def test_vague_message_is_poor():
    result = qc.analyze_message("final commit")
    assert result["score"] == 25
    assert result["rating"] == "poor"
    assert "vague" in codes(result)
    assert result["suggested_subject"] is None
    assert result["suggestions"]


def test_vague_conventional_message_is_capped():
    result = qc.analyze_message("fix: update")
    assert result["is_conventional"] is True
    assert result["score"] == 35
    assert result["rating"] == "poor"


def test_near_miss_prefix():
    result = qc.analyze_message("Fix: crash on empty input")
    assert result["is_conventional"] is False
    assert "malformed_prefix" in codes(result)
    assert "not_conventional" not in codes(result)
    assert result["score"] == 75
    assert result["suggested_subject"] == "fix: crash on empty input"


def test_trailing_period_and_suggestion():
    result = qc.analyze_message("Fix crash on empty input.")
    assert "trailing_period" in codes(result)
    assert result["suggested_subject"] == "fix: crash on empty input"


def test_past_tense_is_flagged():
    result = qc.analyze_message("feat: added login page")
    assert "not_imperative" in codes(result)
    assert result["suggested_subject"] is None  # already conventional


def test_imperative_check_ignores_common_false_positives():
    assert "not_imperative" not in codes(qc.analyze_message("feat: embed the player widget"))
    assert "not_imperative" not in codes(qc.analyze_message("feat: bring back dark mode"))


def test_overlong_subject():
    result = qc.analyze_message("feat: " + "describe the change in great detail " * 3)
    assert "too_long" in codes(result)


def test_unknown_verb_gets_generic_prefix_hint():
    result = qc.analyze_message("Tweak spacing in header")
    assert result["suggested_subject"] is None
    assert any("type prefix" in s for s in result["suggestions"])


def test_empty_message():
    result = qc.analyze_message("  \n ")
    assert result["score"] == 0
    assert "empty_message" in codes(result)


@pytest.mark.parametrize(
    "message, is_merge",
    [
        ("Merge remote changes", True),
        ("Merge branch 'dev' into main", False),
        ("Initial commit", False),
        ('Revert "feat: add login page"', False),
        ("fixup! feat: add login page", False),
    ],
)
def test_auto_generated_messages_are_exempt(message, is_merge):
    result = qc.analyze_message(message, is_merge=is_merge)
    assert result["exempt"] is True
    assert result["score"] is None


# ---- summary ----

def test_summary_counts_and_average():
    analyses = [
        qc.analyze_message("feat: add login page"),
        qc.analyze_message("final commit"),
        qc.analyze_message("Merge remote changes", is_merge=True),
    ]
    summary = qc.summarize(analyses)
    assert summary["total"] == 3
    assert summary["scored"] == 2
    assert summary["exempt"] == 1
    assert summary["average_score"] == 62.5
    assert summary["distribution"] == {"excellent": 1, "good": 0, "fair": 0, "poor": 1}
    assert summary["conventional_count"] == 1
    assert summary["conventional_percent"] == 50.0
    assert summary["vague_count"] == 1


def test_summary_of_nothing():
    summary = qc.summarize([])
    assert summary["total"] == 0
    assert summary["average_score"] is None
    assert summary["conventional_percent"] is None


# ---- API ----

def test_check_endpoint(client):
    response = client.post("/api/quality/check", json={"message": "feat: add login page"})
    assert response.status_code == 200
    assert response.get_json()["score"] == 100


def test_check_endpoint_requires_message(client):
    response = client.post("/api/quality/check", json={})
    assert response.status_code == 400


def test_commits_endpoint_includes_quality(client, tmp_path):
    path = build_repo(tmp_path / "q", ["feat: add login page"])
    data = client.get("/api/commits", query_string={"path": path}).get_json()
    assert data["commits"][0]["quality"]["score"] == 100


def test_summary_endpoint(client, tmp_path):
    path = build_repo(tmp_path / "q", ["Initial commit", "feat: add login page", "final commit"])
    data = client.get("/api/quality/summary", query_string={"path": path}).get_json()
    assert data["analyzed"] == 3
    assert data["truncated"] is False
    assert data["summary"]["scored"] == 2
    assert data["summary"]["exempt"] == 1
    assert data["summary"]["average_score"] == 62.5
    assert data["lowest_scoring"][0]["subject"] == "final commit"


def test_summary_requires_path(client):
    assert client.get("/api/quality/summary").status_code == 400


def test_summary_reports_truncation(tmp_path):
    app = create_app({
        "DATABASE_PATH": tmp_path / "t.db",
        "TESTING": True,
        "MAX_ANALYZED_COMMITS": 2,
    })
    path = build_repo(tmp_path / "q", ["feat: add one", "feat: add two", "feat: add three"])
    data = app.test_client().get("/api/quality/summary", query_string={"path": path}).get_json()
    assert data["analyzed"] == 2
    assert data["total"] == 3
    assert data["truncated"] is True