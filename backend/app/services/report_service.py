"""CSV and repository-health builders.

Pure Python: receives plain dicts and returns text or dicts. No Git and no Flask in here.
"""
import csv
import io
from collections import Counter
from datetime import datetime, timezone

from . import quality_checker

QUALITY_WEIGHT = 70
BRANCH_WEIGHT = 30

ISSUE_LABELS = {
    "not_conventional": "Not in Conventional Commits format",
    "malformed_prefix": "Malformed type prefix",
    "vague": "Vague description",
    "too_short": "Subject too short",
    "too_long": "Subject too long",
    "trailing_period": "Trailing period",
    "not_imperative": "Not in imperative mood",
    "capitalization": "Wrong capitalization",
    "empty_message": "Empty message",
}

_FORMULA_STARTS = ("=", "+", "-", "@", "\t", "\r")
_LEVEL_ORDER = {"error": 0, "warning": 1, "info": 2, "good": 3}

COMMIT_HEADERS = [
    "hash", "short_hash", "date", "author_name", "author_email", "subject", "is_merge",
    "score", "rating", "conventional", "type", "scope", "issues", "suggested_subject",
]
CONTRIBUTOR_HEADERS = [
    "name", "email", "commits", "percent", "merge_commits", "active_days",
    "first_commit", "last_commit", "scored_commits", "average_quality",
]
BRANCH_HEADERS = [
    "name", "is_current", "is_base", "status", "flagged_inactive", "protected",
    "days_since_last_commit", "last_commit_date", "last_commit_hash",
    "last_commit_author", "unmerged_commits",
]


# ---------- CSV ----------

def to_csv(headers, rows):
    """Build CSV text. The leading BOM makes Excel read accents and emoji correctly."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(headers)
    for row in rows:
        writer.writerow([_safe(cell) for cell in row])
    return "\ufeff" + buffer.getvalue()


def _safe(cell):
    """Make a value safe to write into a spreadsheet cell."""
    if cell is None:
        return ""
    if isinstance(cell, bool):
        return "yes" if cell else "no"
    if isinstance(cell, str) and cell.startswith(_FORMULA_STARTS):
        return "'" + cell  # stops Excel from running "=..." as a formula
    return cell


def analyze_commits(commits):
    """Attach a quality analysis to each commit dict."""
    for commit in commits:
        commit["analysis"] = quality_checker.analyze_message(commit["message"], commit["is_merge"])
    return commits


def commits_csv(commits):
    rows = []
    for commit in commits:
        a = commit["analysis"]
        rows.append([
            commit["hash"],
            commit["short_hash"],
            commit["committed_at"].isoformat(),
            commit["author_name"],
            commit["author_email"],
            commit["subject"],
            commit["is_merge"],
            a["score"],
            a["rating"],
            None if a["exempt"] else a["is_conventional"],
            a["type"],
            a["scope"],
            "; ".join(issue["code"] for issue in a["issues"]),
            a["suggested_subject"],
        ])
    return to_csv(COMMIT_HEADERS, rows)


def contributors_csv(contributors):
    rows = [
        [
            c["name"], c["email"], c["commits"], c["percent"], c["merge_commits"],
            c["active_days"], c["first_commit_at"], c["last_commit_at"],
            c["scored_commits"], c["average_quality"],
        ]
        for c in contributors
    ]
    return to_csv(CONTRIBUTOR_HEADERS, rows)


def branches_csv(branches):
    rows = [
        [
            b["name"], b["is_current"], b["is_base"], b["status"], b["flagged_inactive"],
            b["protected"], b["days_since_last_commit"], b["last_commit_date"],
            b["last_commit_hash"], b["last_commit_author"], b["unmerged_commits"],
        ]
        for b in branches
    ]
    return to_csv(BRANCH_HEADERS, rows)


# ---------- health summary ----------

def health_summary(commits, total_commits, contributors, branches, now=None):
    """Combine commits (already analyzed), contributor stats and branch analysis into one report."""
    now = now or datetime.now(timezone.utc)
    summary = quality_checker.summarize([c["analysis"] for c in commits])
    scored = [c for c in commits if not c["analysis"]["exempt"]]
    average = summary["average_score"]

    branch_list = branches["branches"]
    reviewable = [b for b in branch_list if not b["protected"]]
    flagged = [b for b in branch_list if b["flagged_inactive"]]
    if reviewable:
        hygiene = round(100 * (1 - len(flagged) / len(reviewable)), 1)
        hygiene_detail = f"{len(flagged)} of {len(reviewable)} non-protected branches flagged inactive"
    else:
        hygiene = 100.0
        hygiene_detail = "No branches to review"

    score = None
    if average is not None:
        score = round((QUALITY_WEIGHT * average + BRANCH_WEIGHT * hygiene) / 100, 1)

    last_commit = max((c["committed_at"] for c in commits), default=None)
    days_since = max(0, (now - last_commit).days) if last_commit else None
    people = contributors["contributors"]
    top = people[0] if people else None

    counts = Counter(issue["code"] for c in scored for issue in c["analysis"]["issues"])
    breakdown = [
        {
            "code": code,
            "label": ISSUE_LABELS.get(code, code),
            "count": n,
            "percent": round(100 * n / len(scored), 1),
        }
        for code, n in counts.most_common()
    ]

    lowest = sorted(scored, key=lambda c: c["analysis"]["score"])[:10]
    lowest_commits = [
        {
            "hash": c["hash"],
            "short_hash": c["short_hash"],
            "subject": c["subject"],
            "author_name": c["author_name"],
            "committed_at": c["committed_at"].isoformat(),
            "score": c["analysis"]["score"],
            "rating": c["analysis"]["rating"],
            "issues": [issue["message"] for issue in c["analysis"]["issues"]],
            "suggested_subject": c["analysis"]["suggested_subject"],
        }
        for c in lowest
    ]

    findings = _findings(
        summary, scored, average, flagged, reviewable, branches["inactive_days"],
        contributors["contributor_count"], top, last_commit, days_since,
    )

    return {
        "generated_at": now.isoformat(),
        "health": {
            "score": score,
            "grade": _grade(score),
            "components": [
                {
                    "key": "quality", "label": "Commit message quality", "weight": QUALITY_WEIGHT,
                    "score": average,
                    "detail": f"Average of {len(scored)} scored commits" if scored else "No scored commits",
                },
                {
                    "key": "branches", "label": "Branch hygiene", "weight": BRANCH_WEIGHT,
                    "score": hygiene, "detail": hygiene_detail,
                },
            ],
        },
        "metrics": {
            "total_commits": total_commits,
            "analyzed_commits": len(commits),
            "contributor_count": contributors["contributor_count"],
            "branch_count": branches["summary"]["total"],
            "average_quality": average,
            "conventional_percent": summary["conventional_percent"],
            "vague_count": summary["vague_count"],
            "flagged_branches": len(flagged),
            "last_commit_at": last_commit.isoformat() if last_commit else None,
            "days_since_last_commit": days_since,
            "top_contributor": (
                {"name": top["name"], "commits": top["commits"], "percent": top["percent"]} if top else None
            ),
        },
        "findings": findings,
        "issue_breakdown": breakdown,
        "lowest_commits": lowest_commits,
    }


def _grade(score):
    if score is None:
        return "unknown"
    if score >= 75:
        return "healthy"
    if score >= 50:
        return "attention"
    return "at_risk"


def _finding(level, message):
    return {"level": level, "message": message}


def _plural(count, singular, plural):
    return singular if count == 1 else plural


def _ago(days):
    if days == 0:
        return "today"
    return "1 day ago" if days == 1 else f"{days} days ago"


def _findings(summary, scored, average, flagged, reviewable, inactive_days,
              contributor_count, top, last_commit, days_since):
    findings = []

    if average is None:
        findings.append(_finding("info", "No commit messages could be scored: every message is auto-generated."))
    else:
        if average >= 80:
            level, word = "good", "excellent"
        elif average >= 60:
            level, word = "info", "good"
        elif average >= 40:
            level, word = "warning", "fair"
        else:
            level, word = "error", "poor"
        findings.append(_finding(level, f"Average commit message quality is {average}/100 ({word})."))

    percent = summary["conventional_percent"]
    if percent is not None:
        if percent < 50:
            findings.append(_finding(
                "warning",
                f"Only {percent}% of scored commits follow Conventional Commits "
                f"({summary['conventional_count']} of {summary['scored']}).",
            ))
        else:
            findings.append(_finding("good", f"{percent}% of scored commits follow Conventional Commits."))

    vague = summary["vague_count"]
    if vague:
        example = next(
            c["subject"] for c in scored if any(i["code"] == "vague" for i in c["analysis"]["issues"])
        )
        level = "error" if vague / len(scored) >= 0.25 else "warning"
        text = _plural(vague, "commit has a vague message", "commits have vague messages")
        findings.append(_finding(level, f'{vague} {text}, for example "{example}".'))

    if flagged:
        names = [b["name"] for b in flagged]
        shown = ", ".join(names[:5]) + (f" and {len(names) - 5} more" if len(names) > 5 else "")
        text = _plural(len(flagged), "branch has", "branches have")
        findings.append(_finding(
            "warning", f"{len(flagged)} {text} had no commits for over {inactive_days * 2} days: {shown}.",
        ))
    elif reviewable:
        findings.append(_finding("good", "No inactive branches need review."))

    if contributor_count == 1 and top:
        findings.append(_finding("info", f"Single contributor: all commits are by {top['name']}."))
    elif contributor_count >= 2 and top and top["percent"] >= 70:
        findings.append(_finding(
            "warning",
            f"{top['name']} made {top['percent']}% of all commits, so knowledge may be concentrated in one person.",
        ))

    if days_since is not None:
        level = "good" if days_since <= 30 else "info"
        findings.append(_finding(level, f"Last commit was {_ago(days_since)} ({last_commit.date().isoformat()})."))

    findings.sort(key=lambda f: _LEVEL_ORDER[f["level"]])
    return findings