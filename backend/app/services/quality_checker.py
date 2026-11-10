"""Commit message quality checker.

Pure Python: it receives text and returns a score, issues and suggestions.
It knows nothing about Git or Flask, which makes it easy to test.
"""
import re
from collections import Counter

CONVENTIONAL_TYPES = (
    "feat", "fix", "docs", "style", "refactor", "perf",
    "test", "build", "ci", "chore", "revert",
)
_TYPES = "|".join(CONVENTIONAL_TYPES)

# Strict form:  type(scope)!: description   (lowercase type, one space after colon)
CONVENTIONAL_RE = re.compile(
    rf"^(?P<type>{_TYPES})(?:\((?P<scope>[^()\s][^()]*)\))?(?P<breaking>!)?: (?P<description>\S.*)$"
)
# Sloppy form: right type word plus a colon, but wrong case or spacing ("Fix:", "feat:add")
NEAR_MISS_RE = re.compile(
    rf"^(?P<type>{_TYPES})\s*(?:\([^()]*\))?\s*!?\s*:\s*(?P<description>.*)$",
    re.IGNORECASE,
)

# Messages Git or tools write for you. We don't grade these.
_EXEMPT_PATTERNS = (
    (re.compile(r"^Merge (branch|pull request|remote-tracking branch|tag|commit|remote)\b"),
     "Auto-generated merge message"),
    (re.compile(r'^Revert "'), "Auto-generated revert message"),
    (re.compile(r"^(fixup|squash|amend)! "), "Temporary autosquash commit"),
    (re.compile(r"^initial commit$", re.IGNORECASE), "Initial commit"),
)

# A description made ONLY of these words says nothing useful.
VAGUE_WORDS = {
    "fix", "fixes", "fixed", "fixing", "update", "updates", "updated", "updating",
    "change", "changes", "changed", "changing", "edit", "edits", "edited",
    "modify", "modified", "tweak", "tweaks", "cleanup",
    "bug", "bugs", "stuff", "things", "thing", "code", "file", "files",
    "commit", "commits", "final", "first", "last", "latest", "new", "more", "some",
    "minor", "small", "misc", "miscellaneous", "wip", "temp", "tmp",
    "test", "tests", "testing", "work", "working", "done", "finished",
    "again", "please", "asdf",
    "the", "a", "an", "and", "of", "it", "this", "that", "all", "few",
}

# Words that look like past tense / "-ing" but are fine as a first word.
_IMPERATIVE_EXCEPTIONS = {
    "embed", "need", "feed", "speed", "proceed", "succeed", "seed", "bleed", "breed",
    "shed", "bring", "string", "ring", "swing", "spring", "sing", "cling", "fling",
    "sting", "wring", "thing", "during",
}
_THIRD_PERSON = {
    "adds", "fixes", "updates", "removes", "changes", "creates", "implements",
    "improves", "refactors", "deletes", "uses", "makes", "moves", "renames",
    "handles", "cleans", "bumps", "sets", "gets", "allows", "enables", "supports",
    "introduces", "resolves", "corrects", "replaces", "merges", "reverts",
}

_IMPERATIVE_FORMS = {
    "added": "add", "adds": "add", "fixed": "fix", "fixes": "fix",
    "updated": "update", "updates": "update", "removed": "remove", "removes": "remove",
    "changed": "change", "changes": "change", "created": "create", "creates": "create",
    "implemented": "implement", "implements": "implement", "improved": "improve",
    "improves": "improve", "deleted": "delete", "deletes": "delete", "moved": "move",
    "moves": "move", "renamed": "rename", "renames": "rename", "refactored": "refactor",
    "refactors": "refactor", "resolved": "resolve", "resolves": "resolve",
    "bumped": "bump", "bumps": "bump", "upgraded": "upgrade", "upgrades": "upgrade",
    "documented": "document", "tested": "test", "cleaned": "clean",
    "supported": "support", "supports": "support",
}

# Used only to guess a prefix for the "try this instead" suggestion.
_VERB_TO_TYPE = {
    "add": "feat", "implement": "feat", "introduce": "feat", "create": "feat",
    "support": "feat", "enable": "feat", "allow": "feat",
    "fix": "fix", "resolve": "fix", "patch": "fix", "correct": "fix", "repair": "fix",
    "document": "docs", "docs": "docs", "doc": "docs", "readme": "docs",
    "refactor": "refactor", "rename": "refactor", "restructure": "refactor",
    "simplify": "refactor", "extract": "refactor", "move": "refactor",
    "reorganize": "refactor", "clean": "refactor", "cleanup": "refactor",
    "optimize": "perf", "speed": "perf",
    "test": "test",
    "bump": "chore", "upgrade": "chore", "remove": "chore", "delete": "chore",
    "format": "style", "lint": "style",
}


def analyze_message(message, is_merge=False):
    """Score one commit message. Returns a dict (see _result for the keys)."""
    subject = _subject_line(message)

    if not subject:
        return _result(
            score=0,
            issues=[_issue("empty_message", "error", "The commit message is empty.")],
            suggestions=["Write a short summary of what changed and why."],
        )

    reason = _exempt_reason(subject, is_merge)
    if reason:
        return _result(exempt_reason=reason)

    strict = CONVENTIONAL_RE.match(subject)
    near = None if strict else NEAR_MISS_RE.match(subject)
    issues, suggestions = [], []
    commit_type = scope = None
    breaking = False

    # 1. Format (40 points)
    if strict:
        commit_type, scope = strict["type"], strict["scope"]
        breaking = bool(strict["breaking"])
        description = strict["description"].strip()
        format_points = 40
    elif near:
        description = near["description"].strip()
        format_points = 15
        issues.append(_issue(
            "malformed_prefix", "warning",
            "The prefix is close to Conventional Commits but not exact. "
            "Use a lowercase 'type(scope): description' with one space after the colon.",
        ))
    else:
        description = subject
        format_points = 0
        issues.append(_issue(
            "not_conventional", "warning",
            "Does not follow the Conventional Commits format: type(scope): description.",
        ))

    # 2. Description (30 points)
    vague = _is_vague(description)
    if vague:
        description_points = 0
        issues.append(_issue("vague", "error", "The description is too vague to explain what changed."))
    else:
        word_count = len(description.split())
        if word_count == 1:
            description_points = 5
        elif word_count == 2:
            description_points = 15
        else:
            description_points = 30

    # 3. Subject length (15 points)
    length = len(subject)
    if length < 10:
        length_points = 0
        issues.append(_issue("too_short", "error", f"The subject is only {length} characters. Aim for 10 to 50."))
    elif length <= 50:
        length_points = 15
    elif length <= 72:
        length_points = 10
    else:
        length_points = 3
        issues.append(_issue("too_long", "warning", f"The subject is {length} characters. Keep it under 72, ideally 50."))
        suggestions.append("Shorten the subject and move the details into the commit body.")

    # 4. Style (15 points)
    style_points = 0

    if subject.endswith("."):
        issues.append(_issue("trailing_period", "warning", "Remove the period at the end of the subject."))
    else:
        style_points += 5

    first_word_match = re.match(r"[A-Za-z']+", description)
    first_word = first_word_match.group() if first_word_match else ""
    if not first_word or _is_imperative(first_word):
        style_points += 5
    else:
        issues.append(_issue(
            "not_imperative", "warning",
            "Use the imperative mood: 'add login page', not 'added' or 'adds'.",
        ))

    if description:
        first_char = description[0]
        wants_lowercase = bool(strict or near)
        if not first_char.isalpha() or (first_char.islower() if wants_lowercase else first_char.isupper()):
            style_points += 5
        elif wants_lowercase:
            issues.append(_issue("capitalization", "warning", "Start the description after the prefix with a lowercase letter."))
        else:
            issues.append(_issue("capitalization", "warning", "Start the subject with a capital letter."))

    score = format_points + description_points + length_points + style_points
    if vague:
        score = min(score, 35)  # a vague message can never rate better than "poor"

    # Suggestions
    suggested_subject = None
    if vague:
        suggestions.append(
            "Describe what changed and why. Example: 'fix(parser): handle empty input without crashing'."
        )
    elif not strict:
        forced_type = near["type"].lower() if near else None
        suggested_subject = _suggest_subject(description, forced_type)
        if suggested_subject:
            suggestions.append(f"Try: {suggested_subject}")
        else:
            suggestions.append(
                "Add a type prefix such as feat, fix, docs, refactor, test or chore, "
                f"followed by a colon: 'type: {_lowercase_first(description)}'."
            )

    return _result(
        score=score,
        issues=issues,
        suggestions=suggestions,
        is_conventional=bool(strict),
        commit_type=commit_type,
        scope=scope,
        breaking=breaking,
        suggested_subject=suggested_subject,
    )


def summarize(analyses):
    """Combine many analyze_message() results into repository-level numbers."""
    scored = [a for a in analyses if not a["exempt"]]
    distribution = {"excellent": 0, "good": 0, "fair": 0, "poor": 0}
    issue_counts = Counter()
    type_counts = Counter()
    conventional = 0

    for analysis in scored:
        distribution[analysis["rating"]] += 1
        if analysis["is_conventional"]:
            conventional += 1
            type_counts[analysis["type"]] += 1
        for issue in analysis["issues"]:
            issue_counts[issue["code"]] += 1

    count = len(scored)
    return {
        "total": len(analyses),
        "scored": count,
        "exempt": len(analyses) - count,
        "average_score": round(sum(a["score"] for a in scored) / count, 1) if count else None,
        "distribution": distribution,
        "conventional_count": conventional,
        "conventional_percent": round(100 * conventional / count, 1) if count else None,
        "vague_count": issue_counts["vague"],
        "types": dict(type_counts),
        "top_issues": [{"code": code, "count": n} for code, n in issue_counts.most_common(5)],
    }


# ---------- helpers ----------

def _result(score=None, issues=None, suggestions=None, exempt_reason=None,
            is_conventional=False, commit_type=None, scope=None, breaking=False,
            suggested_subject=None):
    """Every analysis has exactly the same keys, so the frontend never has to guess."""
    return {
        "score": score,
        "rating": _rating(score),
        "exempt": exempt_reason is not None,
        "exempt_reason": exempt_reason,
        "is_conventional": is_conventional,
        "type": commit_type,
        "scope": scope,
        "breaking": breaking,
        "issues": issues or [],
        "suggestions": suggestions or [],
        "suggested_subject": suggested_subject,
    }


def _rating(score):
    if score is None:
        return "exempt"
    if score >= 80:
        return "excellent"
    if score >= 60:
        return "good"
    if score >= 40:
        return "fair"
    return "poor"


def _issue(code, severity, message):
    return {"code": code, "severity": severity, "message": message}


def _subject_line(message):
    for line in (message or "").splitlines():
        if line.strip():
            return line.strip()
    return ""


def _exempt_reason(subject, is_merge):
    if is_merge:
        return "Merge commit"
    for pattern, reason in _EXEMPT_PATTERNS:
        if pattern.match(subject):
            return reason
    return None


def _is_vague(description):
    # [^\W_]+ means "letters and digits in any language", so Russian, Hindi or Chinese words count.
    words = re.findall(r"[^\W_]+(?:'[^\W_]+)*", description.lower())
    if not words or len("".join(words)) < 3:
        return True
    return all(word in VAGUE_WORDS for word in words)


def _is_imperative(word):
    """A simple heuristic, not grammar-perfect: flags 'added', 'fixes', 'adding'."""
    w = word.lower()
    if w in _IMPERATIVE_EXCEPTIONS:
        return True
    if w in _THIRD_PERSON:
        return False
    if len(w) >= 4 and (w.endswith("ed") or w.endswith("ing")):
        return False
    return True


def _lowercase_first(text):
    return text[:1].lower() + text[1:]


def _suggest_subject(description, forced_type=None):
    """Build 'type: description' from a plain message, or None if we can't guess the type."""
    words = description.split()
    if not words:
        return None

    first = words[0]
    lowered = first.lower()
    if lowered in _IMPERATIVE_FORMS:
        words[0] = _IMPERATIVE_FORMS[lowered]
    elif first[:1].isupper() and not first[1:2].isupper():  # "Add" -> "add", keep "API"
        words[0] = first[0].lower() + first[1:]

    verb = re.sub(r"[^a-z]", "", words[0].lower())
    commit_type = forced_type or _VERB_TO_TYPE.get(verb)
    if commit_type is None:
        return None

    if commit_type == "fix" and verb == "fix" and len(words) > 1:
        words = words[1:]  # "fix: crash on input", not "fix: fix crash on input"

    return f"{commit_type}: {' '.join(words).rstrip('.')}"