from pathlib import Path

from .errors import ValidationError

MAX_PATH_LENGTH = 1024


def clean_repo_path(raw_path):
    """Check a user-supplied folder path and return it as a clean absolute path."""
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ValidationError("Repository path is required.")

    # Windows "Copy as path" wraps the path in quotes, so strip them.
    cleaned = raw_path.strip().strip('"').strip("'")

    if len(cleaned) > MAX_PATH_LENGTH or "\x00" in cleaned:
        raise ValidationError("Repository path is not valid.")

    path = Path(cleaned).expanduser()
    if not path.exists():
        raise ValidationError(f"Path does not exist: {path}")
    if not path.is_dir():
        raise ValidationError(f"Path is not a folder: {path}")

    return str(path.resolve())


def parse_int(value, default, minimum, maximum, name):
    """Turn a query-string value into an int, enforcing a safe range."""
    if value is None or value == "":
        return default
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{name} must be a whole number.")
    if number < minimum or number > maximum:
        raise ValidationError(f"{name} must be between {minimum} and {maximum}.")
    return number