from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler


class ConflictError(APIException):
    """HTTP 409 — used for booking slot races (FR-122)."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "The requested resource is no longer available."
    default_code = "conflict"


class DomainError(APIException):
    """HTTP 400 for business-rule violations with a clear message."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "The request could not be processed."
    default_code = "domain_error"


def api_exception_handler(exc, context):
    """Wrap DRF's handler to guarantee a consistent error envelope."""
    response = exception_handler(exc, context)
    if response is not None:
        detail = response.data
        code = getattr(exc, "default_code", "error")
        response.data = {
            "error": {
                "code": code,
                "detail": detail.get("detail", detail) if isinstance(detail, dict) else detail,
            }
        }
    return response
