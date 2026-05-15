class AnkaError(Exception):
    """Base ANKA SDK error."""


class AnkaConnectionError(AnkaError):
    """Raised when an ANKA node cannot be reached."""


class AnkaHTTPError(AnkaError):
    """Raised when an ANKA node returns an HTTP error."""

    def __init__(self, status_code: int, message: str, response_text: str = ""):
        super().__init__(f"ANKA HTTP {status_code}: {message}")
        self.status_code = status_code
        self.response_text = response_text


class AnkaRateLimitError(AnkaHTTPError):
    """Raised on HTTP 429."""


class AnkaNotFoundError(AnkaHTTPError):
    """Raised on HTTP 404."""
