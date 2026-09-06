from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from drf_spectacular.generators import SchemaGenerator
from rest_framework.test import APIClient

from chatbot.providers.base import (
    ProviderAuthError,
    ProviderRequestError,
    UnsupportedProviderError,
)
from chatbot.services.chat import RateLimitExceeded


@pytest.fixture
def authenticated_client(db):
    user = get_user_model().objects.create_user(
        email="chat@ex.com",
        password="StrongPass123!",
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
@patch("chatbot.api_views.ChatService.send_message")
def test_v1_chat_requires_jwt_and_byok(mock_send, authenticated_client):
    mock_send.return_value = {"response": "ok", "sources": [], "session_id": "s"}
    anonymous = APIClient()

    assert (
        anonymous.post("/api/v1/chat/", {"message": "hi"}, format="json").status_code
        == 401
    )

    missing_key = authenticated_client.post(
        "/api/v1/chat/",
        {"message": "hi"},
        format="json",
    )
    assert missing_key.status_code == 401

    response = authenticated_client.post(
        "/api/v1/chat/",
        {"message": "hi", "session_id": "s"},
        format="json",
        HTTP_X_API_KEY="sk-test",
        HTTP_X_PROVIDER="gemini",
        HTTP_X_MODEL="gemini-2.5-flash",
        REMOTE_ADDR="192.0.2.1",
    )

    assert response.status_code == 200
    assert response.data["success"] is True
    assert response.data["data"] == {
        "response": "ok",
        "sources": [],
        "session_id": "s",
    }
    mock_send.assert_called_once_with(
        message="hi",
        session_id="s",
        provider_name="gemini",
        api_key="sk-test",
        model="gemini-2.5-flash",
        client_ip="192.0.2.1",
    )


@pytest.mark.django_db
@patch("chatbot.api_views.ChatService.get_history")
def test_v1_chat_history_returns_envelope(mock_history, authenticated_client):
    mock_history.return_value = [{"role": "user", "content": "hi"}]

    response = authenticated_client.get(
        "/api/v1/chat/history/?session_id=s",
        HTTP_X_API_KEY="sk-test",
    )

    assert response.status_code == 200
    assert response.data["data"] == {
        "history": [{"role": "user", "content": "hi"}],
        "session_id": "s",
    }
    mock_history.assert_called_once_with("s")


@pytest.mark.django_db
@patch("chatbot.api_views.ChatService.clear_history")
def test_v1_chat_clear_returns_envelope(mock_clear, authenticated_client):
    mock_clear.return_value = 2

    response = authenticated_client.post(
        "/api/v1/chat/clear/",
        {"session_id": "s"},
        format="json",
        HTTP_X_API_KEY="sk-test",
    )

    assert response.status_code == 200
    assert response.data["data"] == {"deleted": 2, "session_id": "s"}
    mock_clear.assert_called_once_with("s")


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("error", "status"),
    [
        (ValueError("Message cannot be empty."), 400),
        (ProviderAuthError("invalid key"), 401),
        (UnsupportedProviderError("unsupported"), 400),
        (ProviderRequestError("upstream failed"), 502),
        (RateLimitExceeded("Rate limit exceeded"), 429),
    ],
)
@patch("chatbot.api_views.ChatService.send_message")
def test_v1_chat_maps_service_errors(
    mock_send,
    authenticated_client,
    error,
    status,
):
    mock_send.side_effect = error

    response = authenticated_client.post(
        "/api/v1/chat/",
        {"message": "hi", "session_id": "s"},
        format="json",
        HTTP_X_API_KEY="sk-test",
    )

    assert response.status_code == status
    assert response.data["success"] is False
    assert response.data["message"] == str(error)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("method", "path", "data"),
    [
        ("get", "/api/v1/chat/history/?session_id=s", None),
        ("post", "/api/v1/chat/clear/", {"session_id": "s"}),
    ],
)
def test_v1_history_and_clear_require_byok(
    authenticated_client,
    method,
    path,
    data,
):
    response = getattr(authenticated_client, method)(path, data, format="json")

    assert response.status_code == 401
    assert response.data["success"] is False


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("method", "path", "data"),
    [
        ("get", "/api/v1/chat/history/", None),
        ("post", "/api/v1/chat/clear/", {}),
    ],
)
def test_v1_history_and_clear_require_session_id(
    authenticated_client,
    method,
    path,
    data,
):
    response = getattr(authenticated_client, method)(
        path,
        data,
        format="json",
        HTTP_X_API_KEY="sk-test",
    )

    assert response.status_code == 400
    assert response.data["success"] is False


def test_v1_chat_endpoints_are_in_schema():
    paths = SchemaGenerator().get_schema(request=None, public=True)["paths"]

    assert "/api/v1/chat/" in paths
    assert "/api/v1/chat/history/" in paths
    assert "/api/v1/chat/clear/" in paths
