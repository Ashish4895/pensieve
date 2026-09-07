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
        response_text = (_provider_factory or get_provider)(provider_name).complete(
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
