from unittest.mock import MagicMock

import pytest
from django.contrib.auth import get_user_model

from chatbot.models import Message
from chatbot.services.chat import ChatService
from tools.models import ToolDefinition, UserToolPreference
from tools.services.registry import ensure_builtin_server

User = get_user_model()


@pytest.mark.django_db
def test_chat_service_uses_tool_loop_when_gemini_and_tools(monkeypatch):
    user = User.objects.create_user(
        email="u@example.com", password="x", role=User.Role.USER
    )
    server = ensure_builtin_server()
    ToolDefinition.objects.create(
        mcp_server=server,
        name="pensieve_search_documents",
        description="search",
        input_schema={"type": "object"},
        enabled=True,
    )

    class FakeGemini:
        def complete(self, *args, **kwargs):
            raise AssertionError("complete should not be used")

        def complete_with_tools(self, **kwargs):
            assert len(kwargs["tools"]) == 1
            assert kwargs["tools"][0]["name"] == "pensieve_search_documents"
            return kwargs["call_tool"]("pensieve_search_documents", {"query": "hi"})

    out = ChatService.send_message(
        message="ping",
        session_id="s-tools",
        provider_name="gemini",
        api_key="sk-test",
        model=None,
        client_ip="127.0.0.1",
        user=user,
        _rate_limiter=lambda _ip: True,
        _provider_factory=lambda _name: FakeGemini(),
        _retriever=lambda *_a, **_k: [],
        _execute_tool=lambda name, args: f"ran:{name}",
    )

    assert out["response"] == "ran:pensieve_search_documents"
    assert out["tools_available"] == 1
    assert Message.objects.filter(session_id="s-tools").count() == 2


@pytest.mark.django_db
def test_chat_service_skips_tools_for_plain_complete_provider():
    user = User.objects.create_user(
        email="u2@example.com", password="x", role=User.Role.USER
    )
    server = ensure_builtin_server()
    ToolDefinition.objects.create(
        mcp_server=server,
        name="pensieve_search_documents",
        enabled=True,
    )

    class PlainProvider:
        def complete(self, **kwargs):
            return "plain"

    out = ChatService.send_message(
        message="ping",
        session_id="s-plain",
        provider_name="openai",
        api_key="sk-test",
        model=None,
        client_ip="127.0.0.1",
        user=user,
        _rate_limiter=lambda _ip: True,
        _provider_factory=lambda _name: PlainProvider(),
        _retriever=lambda *_a, **_k: [],
    )
    assert out["response"] == "plain"
    assert out["tools_available"] == 1


@pytest.mark.django_db
def test_chat_skips_rag_when_document_search_tool_disabled():
    user = User.objects.create_user(
        email="norag@example.com", password="x", role=User.Role.USER
    )
    server = ensure_builtin_server()
    tool = ToolDefinition.objects.create(
        mcp_server=server,
        name="pensieve_search_documents",
        enabled=True,
    )
    UserToolPreference.objects.create(user=user, tool=tool, enabled=False)

    called = {"rag": False}

    def boom_retriever(*args, **kwargs):
        called["rag"] = True
        return [{"source": "x", "score": 1.0, "content": "secret doc"}]

    class PlainProvider:
        def complete(self, **kwargs):
            assert kwargs["system"] is None
            return "no docs"

    out = ChatService.send_message(
        message="what is in the docs?",
        session_id="s-norag",
        provider_name="openai",
        api_key="sk-test",
        model=None,
        client_ip="127.0.0.1",
        user=user,
        _rate_limiter=lambda _ip: True,
        _provider_factory=lambda _name: PlainProvider(),
        _retriever=boom_retriever,
        _tools_for_user=lambda _u: [],
    )
    assert called["rag"] is False
    assert out["sources"] == []
    assert out["response"] == "no docs"
