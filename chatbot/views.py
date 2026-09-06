import json
import uuid
from django.shortcuts import render
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import ensure_csrf_cookie

from .models import Message
from .providers.base import (
    ChatMessage,
    ProviderAuthError,
    ProviderRequestError,
    UnsupportedProviderError,
)
from .providers.factory import get_provider
from .rag_helper import retrieve_relevant_chunks
from .rate_limit import allow


def _session_id(value):
    return value.strip() if isinstance(value, str) and value.strip() else str(uuid.uuid4())


@ensure_csrf_cookie
def index(request):
    """Render the main chat interface template."""
    return render(request, "chatbot/index.html")

def get_history(request):
    """JSON API to fetch all messages for the current session."""
    session_id = _session_id(request.GET.get("session_id"))
    messages = Message.objects.filter(session_id=session_id).order_by("id")
    history_data = [
        {"role": msg.role, "content": msg.content}
        for msg in messages
    ]
    return JsonResponse({"history": history_data})

def send_message(request):
    """Handle chat using the caller's selected provider and API key."""
    if request.method != "POST":
        return HttpResponseBadRequest("Only POST requests are allowed.")

    try:
        body = json.loads(request.body)
        if not isinstance(body, dict):
            return JsonResponse({"error": "Request payload must be a JSON object."}, status=400)
        user_text = body.get("message", "").strip()
        session_id = _session_id(body.get("session_id"))
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({"error": "Invalid request payload."}, status=400)

    if not user_text:
        return JsonResponse({"error": "Message cannot be empty."}, status=400)

    provider_name = request.headers.get("X-Provider", "gemini")
    api_key = request.headers.get("X-API-Key")
    model = request.headers.get("X-Model")
    if not api_key:
        return JsonResponse({"error": "API key required"}, status=401)

    if not allow(request.META.get("REMOTE_ADDR", "unknown")):
        return JsonResponse({"error": "Rate limit exceeded"}, status=429)

    try:
        # Load previous history for the session from the database
        db_messages = Message.objects.filter(session_id=session_id).order_by("id")
        history = [
            ChatMessage(role=msg.role, content=msg.content)
            for msg in db_messages
        ]

        # RAG Step: Retrieve top relevant chunks matching the user query
        context_items = retrieve_relevant_chunks(user_text, top_k=3, threshold=0.3)
        
        system_instruction = None
        if context_items:
            context_blocks = []
            for item in context_items:
                context_blocks.append(
                    f"[Source File: {item['source']}] (Cosine Similarity: {item['score']:.3f})\n"
                    f"{item['content']}"
                )
            
            context_text = "\n---\n".join(context_blocks)
            system_instruction = f"""You are a helpful assistant. Use the following retrieved document context to help answer the user's question. 
If the answer is not contained in the context, answer based on your general knowledge but start your response by mentioning that the specific detail was not found in the documents.

Retrieved Context:
{context_text}
"""

        history.append(ChatMessage(role="user", content=user_text))

        response_text = get_provider(provider_name).complete(
            messages=history,
            system=system_instruction,
            api_key=api_key,
            model=model,
        )

        # Persist only completed turns so provider failures cannot leave orphaned prompts.
        Message.objects.create(session_id=session_id, role="user", content=user_text)
        Message.objects.create(session_id=session_id, role="model", content=response_text)

        sources = [
            {
                "source": item["source"],
                "score": item["score"],
                "content": item["content"][:200],
            }
            for item in context_items
        ]
        return JsonResponse({"response": response_text, "sources": sources})

    except ProviderAuthError as e:
        return JsonResponse({"error": str(e)}, status=401)
    except UnsupportedProviderError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except ProviderRequestError as e:
        return JsonResponse({"error": str(e)}, status=502)
    except Exception as e:
        return JsonResponse({"error": f"An error occurred: {str(e)}"}, status=500)

def clear_history(request):
    """JSON API to clear history for the session."""
    if request.method != "POST":
        return HttpResponseBadRequest("Only POST requests are allowed.")
    
    try:
        body = json.loads(request.body)
        session_id = _session_id(body.get("session_id"))
    except (json.JSONDecodeError, TypeError):
        session_id = _session_id(None)

    Message.objects.filter(session_id=session_id).delete()
    return JsonResponse({"status": "cleared"})
