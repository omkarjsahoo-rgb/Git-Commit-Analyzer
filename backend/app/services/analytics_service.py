"""Contributor, activity and branch analytics.

Pure Python: receives plain dicts (built by git_service) and returns plain dicts.
No Git and no Flask in here, so it is easy to test.
"""
from collections import Counter
from datetime import datetime, timedelta, timezone

from . import quality_checker

PERIODS = ("daily", "weekly", "monthly")
DEFAULT_PERIODS = {"daily": 90, "weekly": 52, "monthly": 24}
PROTECTED_BRANCHES = {"main", "master", "develop"}


# ---------- contributors ----------

def contributor_stats(records):
    """Group commits by author email (case-insensitive) and total them up."""
    groups = {}
    for record in records:
        group = groups.setdefault(_identity(record), {
            "email": (record["author_email"] or "").strip().lower(),
            "names": Counter(),
            "commits": 0,
            "merges": 0,
            "days": set(),
            "first": None,
            "last": None,
            "scores": [],
        })
        when = record["authored_at"]
        group["names"][(record["author_name"] or "").strip()] += 1
        group["commits"] += 1
        group["days"].add(when.date())
        if group["first"] is None or when < group["first"]:
            group["first"] = when
        if group["last"] is None or when > group["last"]:
            group["last"] = when
        if record["is_merge"]:
            group["merges"] += 1

        analysis = quality_checker.analyze_message(record["message"], record["is_merge"])
        if not analysis["exempt"]:
            group["scores"].append(analysis["score"])

    total = len(records)
    contributors = []
    for group in groups.values():
        scores = group["scores"]
        contributors.append({
            "name": next((n for n, _ in group["names"].most_common() if n), "Unknown"),
            "email": group["email"],
            "commits": group["commits"],
            "percent": round(100 * group["commits"] / total, 1),
            "merge_commits": group["merges"],
            "active_days": len(group["days"]),
            "first_commit_at": group["first"].isoformat(),
            "last_commit_at": group["last"].isoformat(),
            "scored_commits": len(scores),
            "average_quality": round(sum(scores) / len(scores), 1) if scores else None,
        })

    contributors.sort(key=lambda c: (-c["commits"], c["name"].lower()))
    return {
        "total_commits": total,
        "contributor_count": len(contributors),
        "contributors": contributors,
    }


# ---------- activity over time ----------

def activity_series(records, period, periods=None):
    """Count commits per day/week/month, filling quiet periods with zero.

    The range ends at the newest commit and goes back `periods` buckets
    (or to the oldest commit, whichever comes first).
    """
    if period not in PERIODS:
        raise ValueError(f"Unknown period: {period}")
    periods = periods or DEFAULT_PERIODS[period]

    counts = Counter()
    people = {}
    for record in records:
        start = _bucket_start(record["authored_at"].date(), period)
        counts[start] += 1
        people.setdefault(start, set()).add(_identity(record))

    if not counts:
        return {
            "period": period, "labels": [], "commits": [], "active_contributors": [],
            "total_commits": 0, "commits_in_range": 0, "commits_outside_range": 0,
            "range_start": None, "range_end": None, "busiest": None,
        }

    newest, oldest = max(counts), min(counts)
    buckets = [newest]
    while len(buckets) < periods:
        previous = _previous_bucket(buckets[-1], period)
        if previous < oldest:
            break
        buckets.append(previous)
    buckets.reverse()  # oldest first, which is what charts expect

    labels = [_label(b, period) for b in buckets]
    commits = [counts.get(b, 0) for b in buckets]
    active = [len(people.get(b, ())) for b in buckets]
    in_range = sum(commits)
    busiest = max(range(len(commits)), key=lambda i: commits[i])

    return {
        "period": period,
        "labels": labels,
        "commits": commits,
        "active_contributors": active,
        "total_commits": len(records),
        "commits_in_range": in_range,
        "commits_outside_range": len(records) - in_range,
        "range_start": labels[0],
        "range_end": labels[-1],
        "busiest": {"label": labels[busiest], "commits": commits[busiest]},
    }


# ---------- branches ----------

def analyze_branches(branches, base_branch, inactive_days=30, now=None):
    """Label each branch active / stale / inactive. This only labels, it never changes anything.

    active   = last commit less than `inactive_days` ago
    stale    = between `inactive_days` and twice that
    inactive = older than twice `inactive_days`
    The current branch and main/master/develop are never *flagged*,
    because a quiet main branch is normal.
    """
    now = now or datetime.now(timezone.utc)
    summary = {"total": 0, "active": 0, "stale": 0, "inactive": 0, "flagged_inactive": 0}
    entries = []

    for branch in branches:
        days = max(0, (now - branch["last_commit_at"]).days)
        if days < inactive_days:
            status = "active"
        elif days <= 2 * inactive_days:
            status = "stale"
        else:
            status = "inactive"

        protected = branch["is_current"] or branch["name"] in PROTECTED_BRANCHES
        flagged = status == "inactive" and not protected

        summary["total"] += 1
        summary[status] += 1
        summary["flagged_inactive"] += int(flagged)

        entries.append({
            "name": branch["name"],
            "is_current": branch["is_current"],
            "is_base": branch["name"] == base_branch,
            "protected": protected,
            "last_commit_hash": branch["last_commit_hash"],
            "last_commit_date": branch["last_commit_at"].isoformat(),
            "last_commit_author": branch["last_commit_author"],
            "days_since_last_commit": days,
            "status": status,
            "flagged_inactive": flagged,
            "unmerged_commits": branch["unmerged_commits"],
        })

    entries.sort(key=lambda e: (e["days_since_last_commit"], e["name"]))
    return {
        "base_branch": base_branch,
        "inactive_days": inactive_days,
        "summary": summary,
        "branches": entries,
    }


# ---------- helpers ----------

def _identity(record):
    """Who is this? Email first (lowercase), then name, so one person is one row."""
    email = (record["author_email"] or "").strip().lower()
    return email or (record["author_name"] or "").strip().lower() or "unknown"


def _bucket_start(day, period):
    if period == "daily":
        return day
    if period == "weekly":
        return day - timedelta(days=day.weekday())  # the Monday of that week
    return day.replace(day=1)


def _previous_bucket(start, period):
    if period == "daily":
        return start - timedelta(days=1)
    if period == "weekly":
        return start - timedelta(days=7)
    return (start - timedelta(days=1)).replace(day=1)


def _label(start, period):
    return start.strftime("%Y-%m") if period == "monthly" else start.isoformat()