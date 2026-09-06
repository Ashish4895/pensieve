import json
import os
from unittest.mock import MagicMock, patch

import django
import pytest
from django.test import Client, override_settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pensieve.settings")
django.setup()

from chatbot.providers.base import (
    ProviderAuthError,
    ProviderRequestError,
    UnsupportedProviderError,
)
from chatbot.models import Message
from chatbot.rag_helper import get_query_embedding


@pytest.fixture
def client():
    return Client()


def test_send_message_requires_api_key_header(client):
    res = client.post(
        "/api/chat/",
        data=json.dumps({"message": "hi", "session_id": "t1"}),
        content_type="application/json",
        HTTP_X_PROVIDER="gemini",
    )

    assert res.status_code == 401


def test_send_message_rejects_non_object_json(client):
    res = client.post(
        "/api/chat/",
        data=json.dumps([]),
        content_type="application/json",
        HTTP_X_API_KEY="sk-test",
    )

    assert res.status_code == 400
    assert res.json() == {"error": "Request payload must be a JSON object."}


@pytest.mark.django_db
@override_settings(CHAT_RATE_LIMIT=2)
@patch("chatbot.views.retrieve_relevant_chunks", return_value=[])
@patch("chatbot.views.get_provider")
def test_send_message_returns_429_after_limit(mock_get, mock_rag, client):
    mock_get.return_value.complete.return_value = "ok"
    request = {
        "path": "/api/chat/",
        "data": json.dumps({"message": "hi"}),
        "content_type": "application/json",
        "HTTP_X_API_KEY": "sk-test",
        "REMOTE_ADDR": "192.0.2.5",
    }

    assert client.post(**request).status_code == 200
    assert client.post(**request).status_code == 200
    response = client.post(**request)

    assert response.status_code == 429
    assert response.json() == {"error": "Rate limit exceeded"}


@pytest.mark.django_db
@override_settings(CHAT_RATE_LIMIT=2)
@patch("chatbot.views.retrieve_relevant_chunks", return_value=[])
@patch("chatbot.views.get_provider")
def test_send_message_rate_limit_skips_missing_api_key(mock_get, mock_rag, client):
    mock_get.return_value.complete.return_value = "ok"
    keyless = {
        "path": "/api/chat/",
        "data": json.dumps({"message": "hi"}),
        "content_type": "application/json",
        "REMOTE_ADDR": "192.0.2.7",
    }
    with_key = {**keyless, "HTTP_X_API_KEY": "sk-test"}

    for _ in range(5):
        assert client.post(**keyless).status_code == 401

    assert client.post(**with_key).status_code == 200
    assert client.post(**with_key).status_code == 200
    assert client.post(**with_key).status_code == 429


def test_mutating_apis_require_csrf_header():
    csrf_client = Client(enforce_csrf_checks=True)
    index = csrf_client.get("/", HTTP_HOST="localhost")
    token = index.cookies["csrftoken"].value

    blocked = csrf_client.post(
        "/api/chat/",
        data=json.dumps({"message": "hi"}),
        content_type="application/json",
        HTTP_HOST="localhost",
    )
    accepted = csrf_client.post(
        "/api/chat/",
        data=json.dumps({"message": "hi"}),
        content_type="application/json",
        HTTP_HOST="localhost",
        HTTP_X_CSRFTOKEN=token,
        REMOTE_ADDR="192.0.2.6",
    )

    assert blocked.status_code == 403
    assert accepted.status_code == 401


@pytest.mark.django_db
@patch("chatbot.views.retrieve_relevant_chunks", return_value=[])
@patch("chatbot.views.get_provider")
def test_send_message_passes_key_to_provider_without_persisting_it(
    mock_get, mock_rag, client
):
    provider = mock_get.return_value
    provider.complete.return_value = "answer"

    res = client.post(
        "/api/chat/",
        data=json.dumps({"message": "hi", "session_id": "t2"}),
        content_type="application/json",
        HTTP_X_PROVIDER="openai",
        HTTP_X_API_KEY="sk-test",
        HTTP_X_MODEL="gpt-4o-mini",
    )

    assert res.status_code == 200
    assert res.json() == {"response": "answer", "sources": []}
    kwargs = provider.complete.call_args.kwargs
    assert kwargs["api_key"] == "sk-test"
    assert kwargs["model"] == "gpt-4o-mini"
    assert kwargs["messages"][-1].content == "hi"
    persisted_rows = list(Message.objects.filter(session_id="t2"))
    assert [(row.role, row.content) for row in persisted_rows] == [
        ("user", "hi"),
        ("model", "answer"),
    ]
    assert all(
        "sk-test" not in row.content and "sk-test" not in row.session_id
        for row in persisted_rows
    )


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (ProviderAuthError("invalid key"), 401),
        (UnsupportedProviderError("unsupported"), 400),
        (ProviderRequestError("upstream failed"), 502),
    ],
)
@patch("chatbot.views.Message.objects")
@patch("chatbot.views.retrieve_relevant_chunks", return_value=[])
@patch("chatbot.views.get_provider")
def test_send_message_maps_provider_errors(
    mock_get, mock_rag, mock_messages, client, error, status
):
    mock_get.side_effect = error

    res = client.post(
        "/api/chat/",
        data=json.dumps({"message": "hi", "session_id": "errors"}),
        content_type="application/json",
        HTTP_X_API_KEY="secret",
    )

    assert res.status_code == status


@pytest.mark.django_db
@patch("chatbot.views.retrieve_relevant_chunks", return_value=[])
@patch("chatbot.views.get_provider")
def test_provider_failure_does_not_persist_user_message(mock_get, mock_rag, client):
    mock_get.return_value.complete.side_effect = ProviderRequestError("upstream failed")

    res = client.post(
        "/api/chat/",
        data=json.dumps({"message": "hi", "session_id": "failed-turn"}),
        content_type="application/json",
        HTTP_X_API_KEY="secret",
    )

    assert res.status_code == 502
    assert not Message.objects.filter(session_id="failed-turn").exists()


@pytest.mark.django_db
def test_missing_history_session_does_not_use_shared_default(client):
    Message.objects.create(session_id="default", role="user", content="private")

    assert client.get("/api/history/").json() == {"history": []}


def test_query_embedding_uses_server_gemini_key():
    response = MagicMock()
    response.embeddings[0].values = [0.1, 0.2]
    with (
        patch.dict(os.environ, {"GEMINI_API_KEY": "server-key"}),
        patch("chatbot.rag_helper.genai.Client") as client,
    ):
        client.return_value.models.embed_content.return_value = response
        assert get_query_embedding("query") == [0.1, 0.2]

    client.assert_called_once_with(api_key="server-key")
