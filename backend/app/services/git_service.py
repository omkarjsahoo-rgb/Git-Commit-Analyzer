from contextlib import contextmanager
from pathlib import Path

from git import Repo
from git.exc import InvalidGitRepositoryError, NoSuchPathError

from ..utils.errors import RepositoryError, ValidationError

# READ-ONLY RULE: this module only reads. It never commits, checks out,
# deletes, fetches or pushes anything in the analyzed repository.


@contextmanager
def open_repository(path):
    """Open a repo for reading and always release it afterwards.

    Releasing matters on Windows: GitPython keeps background git processes
    open, which can lock files if they are not closed.
    """
    try:
        repo = Repo(path)  # exact folder only, no searching parent folders
    except InvalidGitRepositoryError:
        raise RepositoryError(
            "This folder is not a Git repository. "
            "Select the folder that directly contains the .git directory."
        )
    except NoSuchPathError:
        raise RepositoryError("This path does not exist.")

    if repo.bare:
        repo.close()
        raise RepositoryError(
            "This is a bare repository (it has no working folder). Select a normal clone instead."
        )

    try:
        yield repo
    finally:
        repo.close()


def get_repository_info(repo):
    has_commits = repo.head.is_valid()
    return {
        "name": Path(repo.working_tree_dir).name,
        "path": str(Path(repo.working_tree_dir)),
        "current_branch": _current_branch_name(repo),
        "has_commits": has_commits,
        "total_commits": _count_commits(repo, _revision(repo)) if has_commits else 0,
        "branch_count": len(repo.branches),
    }


def get_commits(repo, limit=100, offset=0, branch=None):
    """Return one page of commits, newest first."""
    if not repo.head.is_valid():  # a brand-new repo with no commits yet
        return {"total": 0, "commits": []}

    rev = _revision(repo, branch)
    branch_map = _build_branch_map(repo)
    commits = [
        _serialize_commit(commit, branch_map)
        for commit in repo.iter_commits(rev, max_count=limit, skip=offset)
    ]
    return {"total": _count_commits(repo, rev), "commits": commits}


def get_branches(repo):
    """List local branches with their most recent commit, newest first."""
    current = _current_branch_name(repo)
    entries = []
    for branch in repo.branches:
        last = branch.commit
        entries.append(
            (
                last.committed_datetime,
                {
                    "name": branch.name,
                    "is_current": branch.name == current,
                    "last_commit_hash": last.hexsha[:7],
                    "last_commit_date": last.committed_datetime.isoformat(),
                    "last_commit_author": _text(last.author.name),
                },
            )
        )
    entries.sort(key=lambda item: item[0], reverse=True)
    return [data for _, data in entries]

def get_commit_messages(repo, branch=None, max_count=5000):
    """Lightweight read of many commits for bulk quality analysis.

    Skips the branch map that get_commits() builds, which is slow on large repos.
    """
    if not repo.head.is_valid():
        return {"total": 0, "commits": []}

    rev = _revision(repo, branch)
    total = _count_commits(repo, rev)
    commits = []
    for commit in repo.iter_commits(rev, max_count=max_count):
        message = _text(commit.message).strip()
        commits.append({
            "hash": commit.hexsha,
            "short_hash": commit.hexsha[:7],
            "subject": message.partition("\n")[0].strip(),
            "message": message,
            "author_name": _text(commit.author.name),
            "committed_at": commit.committed_datetime.isoformat(),
            "is_merge": len(commit.parents) > 1,
        })
    return {"total": total, "commits": commits}

def get_commit_records(repo, branch=None, max_count=5000):
    """Lightweight read of many commits for contributor and activity analytics.

    Returns real datetime objects (not text) so the analytics code can group by date.
    """
    if not repo.head.is_valid():
        return {"total": 0, "commits": []}

    rev = _revision(repo, branch)
    total = _count_commits(repo, rev)
    commits = []
    for commit in repo.iter_commits(rev, max_count=max_count):
        commits.append({
            "author_name": _text(commit.author.name),
            "author_email": _text(commit.author.email),
            "authored_at": commit.authored_datetime,
            "message": _text(commit.message).strip(),
            "is_merge": len(commit.parents) > 1,
        })
    return {"total": total, "commits": commits}


def get_branch_details(repo):
    """Local branches with last-commit info and how many commits are not in the base branch."""
    names = [b.name for b in repo.branches]
    current = _current_branch_name(repo)

    # The "base" is what other branches are compared against.
    base = next((n for n in ("main", "master") if n in names), None)
    if base is None:
        base = current if current in names else (names[0] if names else None)

    details = []
    for branch in repo.branches:
        last = branch.commit
        unmerged = 0
        if base and branch.name != base:
            unmerged = int(repo.git.rev_list(
                "--count", f"refs/heads/{base}..refs/heads/{branch.name}"
            ))
        details.append({
            "name": branch.name,
            "is_current": branch.name == current,
            "last_commit_hash": last.hexsha[:7],
            "last_commit_at": last.committed_datetime,
            "last_commit_author": _text(last.author.name),
            "unmerged_commits": unmerged,
        })
    return {"base_branch": base, "branches": details}

def get_commit_details(repo, branch=None, max_count=5000):
    """Everything the reports need about each commit, newest first (real datetimes, not text)."""
    if not repo.head.is_valid():
        return {"total": 0, "commits": []}

    rev = _revision(repo, branch)
    total = _count_commits(repo, rev)
    commits = []
    for commit in repo.iter_commits(rev, max_count=max_count):
        message = _text(commit.message).strip()
        commits.append({
            "hash": commit.hexsha,
            "short_hash": commit.hexsha[:7],
            "subject": message.partition("\n")[0].strip(),
            "message": message,
            "author_name": _text(commit.author.name),
            "author_email": _text(commit.author.email),
            "authored_at": commit.authored_datetime,
            "committed_at": commit.committed_datetime,
            "is_merge": len(commit.parents) > 1,
        })
    return {"total": total, "commits": commits}

# ---------- helpers ----------

def _text(value):
    """Git can hand back bytes or None; always give the caller a string."""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value or ""


def _current_branch_name(repo):
    try:
        return repo.active_branch.name
    except (TypeError, ValueError):  # detached HEAD has no branch name
        return None


def _revision(repo, branch=None):
    """Decide which commits to read: one branch, all local branches, or HEAD."""
    names = [b.name for b in repo.branches]
    if branch:
        if branch not in names:
            raise ValidationError(f"Branch '{branch}' was not found.")
        return f"refs/heads/{branch}"
    return "--branches" if names else "HEAD"


def _count_commits(repo, rev):
    return int(repo.git.rev_list("--count", rev))


def _build_branch_map(repo):
    """Map each commit hash to the local branches that contain it."""
    mapping = {}
    for branch in repo.branches:
        for sha in repo.git.rev_list(branch.path, "--").splitlines():
            mapping.setdefault(sha, []).append(branch.name)
    return mapping


def _serialize_commit(commit, branch_map):
    message = _text(commit.message).strip()
    subject, _, body = message.partition("\n")
    return {
        "hash": commit.hexsha,
        "short_hash": commit.hexsha[:7],
        "subject": subject.strip(),
        "body": body.strip(),
        "message": message,
        "author_name": _text(commit.author.name),
        "author_email": _text(commit.author.email),
        "authored_at": commit.authored_datetime.isoformat(),
        "committed_at": commit.committed_datetime.isoformat(),
        "is_merge": len(commit.parents) > 1,
        "branches": sorted(branch_map.get(commit.hexsha, [])),
    }