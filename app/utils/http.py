"""Http helpers"""

from typing import Any, Dict
from uuid import uuid4

from fastapi import Request

from app.core.config import settings


def api_success(data: Any = None, *args, **kwargs) -> Dict[str, str]:
    """Send Json API success

    Keyword Arguments:
        data object -- The data to send back (default: {})

    Returns:
        Dict[str, str]
    """
    response = {"success": True, "message": kwargs.get("message") or "Success"}
    response["status_code"] = kwargs.get("status_code", 200)

    if data:
        response["data"] = data

    return response


def api_fail(data: Any = None, *args, **kwargs) -> Dict[str, str]:
    """Send Json API Failure

    Keyword Arguments:
        data object -- The data to send back (default: {})

    Returns:
        Dict[str, str]
    """
    response = {
        "success": False,
        "message": kwargs.get("message") or "Error",
    }

    response["status_code"] = kwargs.get("status_code", 400)

    if data:
        response["data"] = data

    return response


def build_error_response(
    request: Request,
    exc_type: str,
    message: str,
    status_code: int,
) -> Dict[str, Any]:
    """
    Constructs a standardized error response body.

    Args:
        request (Request): The incoming HTTP request.
        exc_type (str): Name/type of the exception.
        detail (str): Detailed error message.
        status_code (int): HTTP status code to return.

    Returns:
        Dict[str, Any]: Structured error response.
    """
    request_id = str(uuid4())
    request.state.request_id = request_id

    data = {
        "request_id": request_id,
    }

    if settings.env != "production":
        data["error"] = exc_type

    return api_fail(
        **{
            # "data": data,
            "status_code": status_code,
            "message": message,
        }
    )
