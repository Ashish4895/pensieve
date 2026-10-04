from collections.abc import Callable

from django.db import transaction
from django.db.models import QuerySet

from ..models import Message
from ..providers.base import ChatMessage, ProviderAuthError
from ..providers.factory import get_provider
from ..rag_helper import retrieve_relevant_chunks
from ..rate_limit import allow


class RateLimitExceeded(Exception):
    pass


def _messages_for(*, session_id, user=None) -> QuerySet[Message]:
    qs = Message.objects.filter(session_id=session_id)
    if user is not None:
        qs = qs.filter(user=user)
    return qs


def _provider_supports_tools(provider) -> bool:
    return any(
        "complete_with_tools" in getattr(cls, "__dict__", {})
        for cls in type(provider).mro()
    )


class ChatService:
    @staticmethod
    def send_message(
        *,
        message,
        session_id,
        provider_name,
        api_key,
        model,
        client_ip,
        user=None,
        _rate_limiter: Callable | None = None,
        _provider_factory: Callable | None = None,
        _retriever: Callable | None = None,
        _tools_for_user: Callable | None = None,
        _execute_tool: Callable | None = None,
    ) -> dict:
        user_text = message.strip() if isinstance(message, str) else ""
        if not user_text:
            raise ValueError("Message cannot be empty.")
        if not api_key:
            raise ProviderAuthError("API key required")

        rate_limiter = _rate_limiter or allow
        if not rate_limiter(client_ip):
            raise RateLimitExceeded("Rate limit exceeded")

        history = [
            ChatMessage(role=item.role, content=item.content)
            for item in _messages_for(session_id=session_id, user=user).order_by("id")
        ]

        tool_defs = []
        if user is not None:
            if _tools_for_user is not None:
                tool_defs = list(_tools_for_user(user))
            else:
                from tools.services.registry import tools_for_user

                tool_defs = list(tools_for_user(user))

        if user is None:
            allow_doc_search = True
        else:
            from tools.services.registry import document_search_enabled_for

            allow_doc_search = document_search_enabled_for(user)

        context_items = []
        if allow_doc_search:
            context_items = (_retriever or retrieve_relevant_chunks)(
                user_text, top_k=3, threshold=0.3
            )

        system_instruction = None
        if context_items:
            context_text = "\n---\n".join(
                f"[Source File: {item['source']}] "
                f"(Cosine Similarity: {item['score']:.3f})\n{item['content']}"
                for item in context_items
            )
            system_instruction = (
                "You are a helpful assistant. Use the following retrieved document "
                "context to help answer the user's question. \n"
                "If the answer is not contained in the context, answer based on your "
                "general knowledge but start your response by mentioning that the "
                "specific detail was not found in the documents.\n\n"
                f"Retrieved Context:\n{context_text}\n"
            )

        history.append(ChatMessage(role="user", content=user_text))
        provider = (_provider_factory or get_provider)(provider_name)

        tools_payload = [
            {
                "name": t.name,
                "description": t.description or t.title or t.name,
                "input_schema": t.input_schema or {"type": "object"},
            }
            for t in tool_defs
        ]

        if tools_payload and _provider_supports_tools(provider):
            execute = _execute_tool
            if execute is None:
                from tools.services.registry import execute_tool as registry_execute

                def execute(name, args, _user=user):
                    return registry_execute(user=_user, name=name, arguments=args)

            response_text = provider.complete_with_tools(
                messages=history,
                system=system_instruction,
                api_key=api_key,
                model=model,
                tools=tools_payload,
                call_tool=execute,
            )
        else:
            response_text = provider.complete(
                messages=history,
                system=system_instruction,
                api_key=api_key,
                model=model,
            )

        with transaction.atomic():
            Message.objects.create(
                session_id=session_id,
                user=user,
                role="user",
                content=user_text,
            )
            Message.objects.create(
                session_id=session_id,
                user=user,
                role="model",
                content=response_text,
            )

        sources = [
            {
                "source": item["source"],
                "score": item["score"],
                "content": item["content"][:200],
            }
            for item in context_items
        ]
        return {
            "response": response_text,
            "sources": sources,
            "session_id": session_id,
            "tools_available": len(tools_payload),
        }

    @staticmethod
    def get_history(session_id, *, user=None) -> list[dict]:
        return list(
            _messages_for(session_id=session_id, user=user)
            .order_by("id")
            .values("role", "content")
        )

    @staticmethod
    def clear_history(session_id, *, user=None) -> int:
        deleted_count, _ = _messages_for(session_id=session_id, user=user).delete()
        return deleted_count
