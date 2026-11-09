class AppError(Exception):
    """Base class for errors we want to show the user as clean JSON."""

    status_code = 400

    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code


class ValidationError(AppError):
    """The request is missing data or the data is malformed."""

    status_code = 400


class RepositoryError(AppError):
    """The path exists but is not a usable Git repository."""

    status_code = 422