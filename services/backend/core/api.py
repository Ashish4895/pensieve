from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from rest_framework.views import exception_handler


def api_success(data=None, message="Success", status_code=HTTP_200_OK):
    return Response(
        {
            "success": True,
            "message": message,
            "data": data,
            "errors": None,
        },
        status=status_code,
    )


def api_error(message="Request failed", errors=None, status_code=HTTP_400_BAD_REQUEST):
    return Response(
        {
            "success": False,
            "message": message,
            "data": None,
            "errors": errors,
        },
        status=status_code,
    )


def _message_from_drf_data(data):
    if isinstance(data, dict):
        detail = data.get("detail", data.get("non_field_errors"))
        if isinstance(detail, str):
            return detail
        if isinstance(detail, list):
            return " ".join(str(item) for item in detail)
    return "Request failed"


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None

    return api_error(
        message=_message_from_drf_data(response.data),
        errors=response.data,
        status_code=response.status_code,
    )
