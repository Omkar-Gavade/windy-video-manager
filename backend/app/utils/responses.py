"""Response envelope helpers and the application error type.

Every endpoint returns a consistent shape:

    success -> {"success": True, "data": <payload>}
    error   -> {"success": False, "message": <human message>}

Routes build success envelopes; errors are produced centrally by the
exception handlers wired to ``AppError`` (registered in a later milestone).
"""

from typing import Any


class AppError(Exception):
    """Domain error carrying an HTTP status and a safe, user-facing message.

    Services raise this instead of leaking boto3 / stack-trace details. The
    ``message`` is intended to be shown to the user as-is.
    """

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def success(data: Any) -> dict[str, Any]:
    """Build a success envelope."""
    return {"success": True, "data": data}


def error(message: str) -> dict[str, Any]:
    """Build an error envelope."""
    return {"success": False, "message": message}
