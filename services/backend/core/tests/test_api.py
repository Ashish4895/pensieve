from django.conf import settings
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.status import HTTP_201_CREATED, HTTP_400_BAD_REQUEST

from core.api import api_error, api_success, custom_exception_handler


def test_custom_exception_handler_is_configured():
    assert (
        settings.REST_FRAMEWORK["EXCEPTION_HANDLER"]
        == "core.api.custom_exception_handler"
    )


def test_api_success_returns_standard_envelope():
    response = api_success(
        data={"id": 1},
        message="Created",
        status_code=HTTP_201_CREATED,
    )

    assert response.status_code == HTTP_201_CREATED
    assert response.data == {
        "success": True,
        "message": "Created",
        "data": {"id": 1},
        "errors": None,
    }


def test_api_error_returns_standard_envelope():
    response = api_error(
        message="Invalid request",
        errors={"name": ["This field is required."]},
    )

    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.data == {
        "success": False,
        "message": "Invalid request",
        "data": None,
        "errors": {"name": ["This field is required."]},
    }


def test_custom_exception_handler_wraps_drf_field_errors():
    response = custom_exception_handler(
        ValidationError({"name": ["This field is required."]}),
        {},
    )

    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.data == {
        "success": False,
        "message": "Request failed",
        "data": None,
        "errors": {"name": ["This field is required."]},
    }


def test_custom_exception_handler_uses_drf_detail_message():
    response = custom_exception_handler(NotFound("Widget not found."), {})

    assert response.status_code == 404
    assert response.data == {
        "success": False,
        "message": "Widget not found.",
        "data": None,
        "errors": {"detail": "Widget not found."},
    }
