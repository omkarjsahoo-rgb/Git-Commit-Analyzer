from pathlib import Path

import pytest
from git import Actor, Repo

from app import create_app
from app.services import git_service
from app.utils.errors import RepositoryError, ValidationError
from app.utils.validators import clean_repo_path

AUTHOR = Actor("Test User", "test@example.com")


def make_commit(repo, filename, message):
    (Path(repo.working_tree_dir) / filename).write_text(message)
    repo.index.add([filename])
    return repo.index.commit(message, author=AUTHOR, committer=AUTHOR)


@pytest.fixture
def sample_repo(tmp_path):
    """A temporary repo with 2 commits and 2 branches (main, feature/x)."""
    repo = Repo.init(tmp_path / "sample")
    make_commit(repo, "a.txt", "feat: add a")
    make_commit(repo, "b.txt", "fix: fix b")
    repo.git.branch("-M", "main")
    repo.git.branch("feature/x")
    yield repo
    repo.close()


@pytest.fixture
def client(tmp_path):
    app = create_app({"DATABASE_PATH": tmp_path / "test.db", "TESTING": True})
    return app.test_client()


# ---- validators ----

def test_empty_path_rejected():
    with pytest.raises(ValidationError):
        clean_repo_path("   ")


def test_missing_path_rejected(tmp_path):
    with pytest.raises(ValidationError):
        clean_repo_path(str(tmp_path / "does-not-exist"))


def test_quotes_are_stripped(tmp_path):
    assert clean_repo_path(f'"{tmp_path}"') == str(tmp_path.resolve())


# ---- git service ----

def test_non_git_folder_rejected(tmp_path):
    with pytest.raises(RepositoryError):
        with git_service.open_repository(str(tmp_path)):
            pass


def test_repository_info(sample_repo):
    with git_service.open_repository(sample_repo.working_tree_dir) as repo:
        info = git_service.get_repository_info(repo)
    assert info["total_commits"] == 2
    assert info["branch_count"] == 2
    assert info["current_branch"] == "main"


def test_commits_newest_first_with_branches(sample_repo):
    with git_service.open_repository(sample_repo.working_tree_dir) as repo:
        result = git_service.get_commits(repo, limit=10, offset=0)
    assert result["total"] == 2
    assert result["commits"][0]["subject"] == "fix: fix b"
    assert result["commits"][0]["branches"] == ["feature/x", "main"]
    assert result["commits"][0]["author_name"] == "Test User"


def test_pagination(sample_repo):
    with git_service.open_repository(sample_repo.working_tree_dir) as repo:
        result = git_service.get_commits(repo, limit=1, offset=1)
    assert result["total"] == 2
    assert [c["subject"] for c in result["commits"]] == ["feat: add a"]


def test_unknown_branch_rejected(sample_repo):
    with git_service.open_repository(sample_repo.working_tree_dir) as repo:
        with pytest.raises(ValidationError):
            git_service.get_commits(repo, branch="nope")


def test_empty_repository(tmp_path):
    Repo.init(tmp_path / "empty").close()
    with git_service.open_repository(str(tmp_path / "empty")) as repo:
        info = git_service.get_repository_info(repo)
        commits = git_service.get_commits(repo)
    assert info["has_commits"] is False
    assert info["total_commits"] == 0
    assert commits == {"total": 0, "commits": []}


def test_analysis_does_not_modify_repository(sample_repo):
    head_before = sample_repo.head.commit.hexsha
    with git_service.open_repository(sample_repo.working_tree_dir) as repo:
        git_service.get_commits(repo)
        git_service.get_branches(repo)
    assert sample_repo.head.commit.hexsha == head_before
    assert sorted(b.name for b in sample_repo.branches) == ["feature/x", "main"]


# ---- API ----

def test_open_endpoint(client, sample_repo):
    response = client.post("/api/repository/open", json={"path": sample_repo.working_tree_dir})
    assert response.status_code == 200
    assert response.get_json()["repository"]["total_commits"] == 2

    recent = client.get("/api/repository/recent").get_json()["repositories"]
    assert len(recent) == 1


def test_open_endpoint_requires_path(client):
    response = client.post("/api/repository/open", json={})
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_open_endpoint_rejects_non_repo(client, tmp_path):
    response = client.post("/api/repository/open", json={"path": str(tmp_path)})
    assert response.status_code == 422


def test_commits_endpoint(client, sample_repo):
    response = client.get("/api/commits", query_string={"path": sample_repo.working_tree_dir, "limit": 1})
    data = response.get_json()
    assert response.status_code == 200
    assert data["total"] == 2
    assert len(data["commits"]) == 1


def test_commits_endpoint_rejects_bad_limit(client, sample_repo):
    response = client.get("/api/commits", query_string={"path": sample_repo.working_tree_dir, "limit": 9999})
    assert response.status_code == 400


def test_branches_endpoint(client, sample_repo):
    response = client.get("/api/branches", query_string={"path": sample_repo.working_tree_dir})
    names = {b["name"] for b in response.get_json()["branches"]}
    assert names == {"main", "feature/x"}