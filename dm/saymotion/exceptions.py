"""Custom exceptions for Saymotion API."""


class SaymotionError(Exception):
    """Base exception for all Saymotion API errors."""

    pass


class AuthenticationError(SaymotionError):
    """Raised when authentication fails."""

    pass


class APIError(SaymotionError):
    """Raised when API call fails with an error code."""

    def __init__(self, message: str, status_code: int = None, error_code: int = None):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code


class ValidationError(SaymotionError):
    """Raised when input validation fails."""

    pass


class TimeoutError(SaymotionError):
    """Raised when operation times out."""

    def __init__(self, message: str, rid: str = None):
        super().__init__(message)
        self.rid = rid
