"""Domain errors. Services raise these; main.py maps them to HTTP responses,
so the business layer does not depend on FastAPI."""


class AppError(Exception):
    status_code = 500
    detail = "Internal server error"
    headers: dict[str, str] | None = None

    def __init__(self, detail: str | None = None, headers: dict[str, str] | None = None):
        self.detail = detail or self.detail
        if headers is not None:
            self.headers = headers
        super().__init__(self.detail)


class NotFoundError(AppError):
    status_code = 404
    detail = "Not found"


class ConflictError(AppError):
    status_code = 409
    detail = "Conflict"


class UnauthorizedError(AppError):
    status_code = 401
    detail = "Unauthorized"
    headers = {"WWW-Authenticate": "Bearer"}


class RateLimitError(AppError):
    status_code = 429
    detail = "Too many requests"
