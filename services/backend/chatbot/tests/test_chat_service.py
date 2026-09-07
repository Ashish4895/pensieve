from unittest.mock import patch

import pytest

from chatbot.models import Message
from chatbot.providers.base import ProviderRequestError


@pytest.mark.django_db
@patch("chatbot.services.chat.retrieve_relevant_chunks", return_value=[])
@patch("chatbot.services.chat.get_provider")
@patch("chatbot.services.chat.allow", return_value=True)
def test_chat_service_persists_after_success(mock_allow, mock_get, mock_rag):
    mock_get.return_value.complete.return_value = "pong"
    from chatbot.services.chat import ChatService

    out = ChatService.send_message(
        message="ping",
        session_id="s1",
        provider_name="gemini",
        api_key="sk-test",
        model=None,
        client_ip="127.0.0.1",
    )

    assert out == {"response": "pong", "sources": [], "session_id": "s1"}
    assert list(
        Message.objects.filter(session_id="s1").values_list("role", "content")
    ) == [("user", "ping"), ("model", "pong")]


@pytest.mark.django_db
@patch("chatbot.services.chat.retrieve_relevant_chunks", return_value=[])
@patch("chatbot.services.chat.get_provider")
@patch("chatbot.services.chat.allow", return_value=True)
def test_chat_service_does_not_persist_failed_turn(mock_allow, mock_get, mock_rag):
    mock_get.return_value.complete.side_effect = ProviderRequestError("failed")
    from chatbot.services.chat import ChatService

    with pytest.raises(ProviderRequestError, match="failed"):
        ChatService.send_message(
            message="ping",
            session_id="s1",
            provider_name="gemini",
            api_key="sk-test",
            model=None,
            client_ip="127.0.0.1",
        )

    assert not Message.objects.filter(session_id="s1").exists()


@pytest.mark.django_db
@patch("chatbot.services.chat.allow", return_value=False)
def test_chat_service_raises_rate_limit_error(mock_allow):
    from chatbot.services.chat import ChatService, RateLimitExceeded

    with pytest.raises(RateLimitExceeded, match="Rate limit exceeded"):
        ChatService.send_message(
            message="ping",
            session_id="s1",
            provider_name="gemini",
            api_key="sk-test",
            model=None,
            client_ip="127.0.0.1",
        )

    assert not Message.objects.filter(session_id="s1").exists()


@pytest.mark.django_db
def test_chat_service_gets_and_clears_history():
    from chatbot.services.chat import ChatService

    Message.objects.create(session_id="s1", role="user", content="ping")
    Message.objects.create(session_id="s1", role="model", content="pong")

    assert ChatService.get_history("s1") == [
        {"role": "user", "content": "ping"},
        {"role": "model", "content": "pong"},
    ]
    assert ChatService.clear_history("s1") == 2
    assert not Message.objects.filter(session_id="s1").exists()


@pytest.mark.django_db
@patch("chatbot.services.chat.retrieve_relevant_chunks", return_value=[])
@patch("chatbot.services.chat.get_provider")
@patch("chatbot.services.chat.allow", return_value=True)
def test_chat_service_scopes_history_to_user(mock_allow, mock_get, mock_rag, django_user_model):
    mock_get.return_value.complete.return_value = "mine"
    from chatbot.services.chat import ChatService

    alice = django_user_model.objects.create_user(
        email="alice@ex.com", password="StrongPass123!"
    )
    bob = django_user_model.objects.create_user(
        email="bob@ex.com", password="StrongPass123!"
    )
    Message.objects.create(
        session_id="shared", user=bob, role="user", content="bob secret"
    )

    ChatService.send_message(
        message="hi",
        session_id="shared",
        provider_name="gemini",
        api_key="sk-test",
        model=None,
        client_ip="127.0.0.1",
        user=alice,
    )

    assert ChatService.get_history("shared", user=alice) == [
        {"role": "user", "content": "hi"},
        {"role": "model", "content": "mine"},
    ]
    assert ChatService.get_history("shared", user=bob) == [
        {"role": "user", "content": "bob secret"},
    ]
    assert ChatService.clear_history("shared", user=alice) == 2
    assert Message.objects.filter(session_id="shared", user=bob).count() == 1
