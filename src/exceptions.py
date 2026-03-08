"""
KrishiMandal — Custom exception classes.
"""
from __future__ import annotations


class KrishiMandalError(Exception):
    """Base exception for KrishiMandal."""
    status_code: int = 500
    detail: str = "Internal server error"

    def __init__(self, detail: str | None = None):
        self.detail = detail or self.__class__.detail
        super().__init__(self.detail)


class FarmNotFoundError(KrishiMandalError):
    status_code = 404
    detail = "Farm or farmer not found"


class InvalidInputError(KrishiMandalError):
    status_code = 422
    detail = "Invalid input provided"


class ServiceUnavailableError(KrishiMandalError):
    status_code = 503
    detail = "External service temporarily unavailable"
