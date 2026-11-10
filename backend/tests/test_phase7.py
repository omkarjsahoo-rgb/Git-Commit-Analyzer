import csv
import hashlib
import io
from pathlib import Path

import pytest
from git import Actor, Repo
from git.exc import GitCommandError

from app import create_app
from app.services import git_service, quality_checker

AUTHOR = Actor("Test User", "test@example.com")


def build_repo(path, items):
    """Throwaway repo. Each item is a message or a (message, Actor) pair, oldest first."""
    repo = Repo.init(path)
    for i, item in enumerate(items):
        message, actor = item if isinstance(item, tuple) else (item, AUTHOR)
        name = f"f{i}.txt"
        (Path(path) / name).write_text(message, encoding="utf-8")
        repo.index.add([name])
        repo.index.commit(message, author=actor, committer=actor)
    repo.git.branch("-M", "main")
    repo.close()
    return str(path)


def issue_codes(result):
    return [issue["code"] for issue in result["issues"]]


def fingerprint(path):
    """A hash of every file in the repository folder (including .git), to detect any change."""
    return {
        str(file.relative_to(path)): hashlib.sha1(file.read_bytes()).hexdigest()
        for file in sorted(Path(path).rglob("*"))
        if file.is_file()
    }


@pytest.fixture
def client(tmp_path):
    app = create_app({"DATABASE_PATH": tmp_path / "test.db", "TESTING": True})
    return app.test_client()


# ---- unusual input ----

def test_unicode_authors_and_messages_survive_api_and_csv(client, tmp_path):
    zoe = Actor("Zoë Müller", "zoe@example.com")
    path = build_repo(tmp_path / "uni", [("feat: добавить вход 🚀", zoe)])

    commit = client.get("/api/commits", query_string={"path": path}).get_json()["commits"][0]
    assert commit["subject"] == "feat: добавить вход 🚀"
    assert commit["author_name"] == "Zoë Müller"
    assert "vague" not in issue_codes(commit["quality"])

    text = client.get("/api/reports/commits.csv", query_string={"path": path}).get_data(as_text=True)
    row = next(csv.DictReader(io.StringIO(text.lstrip("\ufeff"))))
    assert row["subject"] == "feat: добавить вход 🚀"
    assert row["author_name"] == "Zoë Müller"


def test_folder_names_with_spaces_and_accents_work(client, tmp_path):
    path = build_repo(tmp_path / "my projét", ["feat: add login page"])
    data = client.post("/api/repository/open", json={"path": path}).get_json()
    assert data["repository"]["name"] == "my projét"


def test_detached_head_is_supported(client, tmp_path):
    path = build_repo(tmp_path / "d", ["feat: add one", "fix: fix two"])
    git_repo = Repo(path)
    git_repo.git.checkout(git_repo.head.commit.parents[0].hexsha)
    git_repo.close()

    info = client.post("/api/repository/open", json={"path": path}).get_json()["repository"]
    assert info["current_branch"] is None
    assert info["total_commits"] == 2

    assert client.get("/api/commits", query_string={"path": path}).status_code == 200
    analysis = client.get("/api/branches/analysis", query_string={"path": path}).get_json()
    assert analysis["base_branch"] == "main"


def test_bare_repository_gets_a_clear_error(client, tmp_path):
    Repo.init(tmp_path / "bare.git", bare=True).close()
    response = client.post("/api/repository/open", json={"path": str(tmp_path / "bare.git")})
    assert response.status_code == 422
    assert "bare" in response.get_json()["error"].lower()


def test_dubious_ownership_gets_a_helpful_message(client, tmp_path, monkeypatch):
    path = build_repo(tmp_path / "o", ["feat: add one"])

    def refuse(*args, **kwargs):
        raise GitCommandError("rev-list", 128, stderr="fatal: detected dubious ownership in repository at 'X'")

    monkeypatch.setattr(git_service, "get_commits", refuse)
    response = client.get("/api/commits", query_string={"path": path})
    assert response.status_code == 422
    assert "safe.directory" in response.get_json()["error"]


# ---- empty repositories ----

EMPTY_REPO_ENDPOINTS = [
    ("/api/commits", {}),
    ("/api/commits", {"rating": "poor"}),
    ("/api/quality/summary", {}),
    ("/api/contributors", {}),
    ("/api/activity", {}),
    ("/api/branches", {}),
    ("/api/branches/analysis", {}),
    ("/api/reports/health", {}),
    ("/api/reports/commits.csv", {}),
    ("/api/reports/contributors.csv", {}),
    ("/api/reports/branches.csv", {}),
    ("/api/reports/snapshots", {}),
]


@pytest.mark.parametrize("url, params", EMPTY_REPO_ENDPOINTS)
def test_empty_repository_never_causes_errors(client, tmp_path, url, params):
    path = tmp_path / "empty"
    Repo.init(path).close()
    response = client.get(url, query_string={"path": str(path), **params})
    assert response.status_code == 200


# ---- host check ----

def test_requests_for_other_hostnames_are_rejected(client):
    assert client.get("/api/health").status_code == 200
    response = client.get("/api/health", base_url="http://evil.example")
    assert response.status_code == 403
    assert "error" in response.get_json()


def test_loopback_addresses_are_allowed(client):
    for base in ("http://127.0.0.1:5001", "http://localhost:5173"):
        assert client.get("/api/health", base_url=base).status_code == 200


# ---- the read-only promise ----

READ_ONLY_ENDPOINTS = [
    ("/api/commits", {}),
    ("/api/commits", {"q": "final", "rating": "poor"}),
    ("/api/quality/summary", {}),
    ("/api/contributors", {}),
    ("/api/activity", {"period": "daily"}),
    ("/api/activity", {"period": "weekly"}),
    ("/api/activity", {"period": "monthly"}),
    ("/api/branches", {}),
    ("/api/branches/analysis", {}),
    ("/api/reports/health", {}),
    ("/api/reports/commits.csv", {}),
    ("/api/reports/contributors.csv", {}),
    ("/api/reports/branches.csv", {}),
]


def test_every_endpoint_leaves_the_repository_untouched(client, tmp_path):
    path = build_repo(tmp_path / "ro", ["feat: add one", "final commit", "fix: handle empty input"])
    git_repo = Repo(path)
    git_repo.git.branch("feature/x")
    git_repo.close()

    before = fingerprint(path)

    assert client.post("/api/repository/open", json={"path": path}).status_code == 200
    for url, params in READ_ONLY_ENDPOINTS:
        response = client.get(url, query_string={"path": path, **params})
        assert response.status_code == 200, url
    assert client.post("/api/reports/snapshots", json={"path": path}).status_code == 201

    assert fingerprint(path) == before


# ---- quality checker: language handling ----

def test_non_english_descriptions_are_not_vague():
    result = quality_checker.analyze_message("feat: добавить вход")
    assert "vague" not in issue_codes(result)


def test_emoji_only_description_is_vague():
    assert "vague" in issue_codes(quality_checker.analyze_message("feat: 🚀"))


def test_underscored_filler_words_are_still_vague():
    assert "vague" in issue_codes(quality_checker.analyze_message("fix: fix_bug"))