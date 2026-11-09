from pathlib import Path

import pytest
from git import Actor, Repo

from app import create_app

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


@pytest.fixture
def client(tmp_path):
    app = create_app({"DATABASE_PATH": tmp_path / "test.db", "TESTING": True})
    return app.test_client()


@pytest.fixture
def repo_path(tmp_path):
    # Newest first this reads: fix, final commit, feat
    return build_repo(tmp_path / "r", [
        "feat: add login page",
        ("final commit", OTHER),
        "fix: handle empty input",
    ])


def get(client, path, **params):
    return client.get("/api/commits", query_string={"path": path, **params})


def subjects(response):
    return [c["subject"] for c in response.get_json()["commits"]]


def test_search_message_is_case_insensitive(client, repo_path):
    response = get(client, repo_path, q="LOGIN")
    data = response.get_json()
    assert data["total"] == 1
    assert subjects(response) == ["feat: add login page"]
    assert data["commits"][0]["quality"]["score"] == 100


def test_search_by_author(client, repo_path):
    response = get(client, repo_path, q="jane")
    assert subjects(response) == ["final commit"]


def test_search_by_hash_prefix(client, repo_path):
    newest = get(client, repo_path).get_json()["commits"][0]
    response = get(client, repo_path, q=newest["hash"][:8])
    assert response.get_json()["total"] == 1
    assert subjects(response) == ["fix: handle empty input"]


def test_search_with_no_match(client, repo_path):
    data = get(client, repo_path, q="zzz-nothing").get_json()
    assert data["total"] == 0
    assert data["commits"] == []


def test_rating_poor(client, repo_path):
    assert subjects(get(client, repo_path, rating="poor")) == ["final commit"]


def test_rating_excellent(client, repo_path):
    response = get(client, repo_path, rating="excellent")
    assert response.get_json()["total"] == 2


def test_rating_exempt(client, tmp_path):
    path = build_repo(tmp_path / "e", ["Initial commit", "feat: add thing"])
    assert subjects(get(client, path, rating="exempt")) == ["Initial commit"]


def test_search_and_rating_combine(client, repo_path):
    assert get(client, repo_path, q="jane", rating="excellent").get_json()["total"] == 0


def test_filtered_pagination(client, repo_path):
    response = get(client, repo_path, rating="excellent", limit=1, offset=1)
    assert response.get_json()["total"] == 2
    assert subjects(response) == ["feat: add login page"]


def test_invalid_rating_rejected(client, repo_path):
    assert get(client, repo_path, rating="amazing").status_code == 400


def test_overlong_search_rejected(client, repo_path):
    assert get(client, repo_path, q="x" * 201).status_code == 400


def test_unfiltered_response_is_not_truncated(client, repo_path):
    assert get(client, repo_path).get_json()["truncated"] is False


def test_filtered_search_reports_truncation(tmp_path, repo_path):
    app = create_app({
        "DATABASE_PATH": tmp_path / "t.db",
        "TESTING": True,
        "MAX_ANALYZED_COMMITS": 2,
    })
    data = get(app.test_client(), repo_path, rating="excellent").get_json()
    assert data["total"] == 1  # only the newest 2 commits were scanned
    assert data["truncated"] is True