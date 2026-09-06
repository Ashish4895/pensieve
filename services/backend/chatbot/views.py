import json
import uuid
from django.shortcuts import render
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import ensure_csrf_cookie

from .models import Message
from .providers.base import (
    ProviderAuthError,
    ProviderRequestError,
    UnsupportedProviderError,
)
# Keep these aliases as the legacy view's injectable dependencies.
from .providers.factory import get_provider
from .rag_helper import retrieve_relevant_chunks
from .rate_limit import allow
from .services.chat import ChatService, RateLimitExceeded


def _session_id(value):
    return value.strip() if isinstance(value, str) and value.strip() else str(uuid.uuid4())


@ensure_csrf_cookie
def index(request):
    """Render the main chat interface template."""
    return render(request, "chatbot/index.html")

def get_history(request):
    """JSON API to fetch all messages for the current session."""
    session_id = _session_id(request.GET.get("session_id"))
    return JsonResponse({"history": ChatService.get_history(session_id)})

def send_message(request):
    """Handle chat using the caller's selected provider and API key."""
    if request.method != "POST":
        return HttpResponseBadRequest("Only POST requests are allowed.")

    try:
        body = json.loads(request.body)
        if not isinstance(body, dict):
            return JsonResponse({"error": "Request payload must be a JSON object."}, status=400)
        user_text = body.get("message", "")
        session_id = _session_id(body.get("session_id"))
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({"error": "Invalid request payload."}, status=400)

    provider_name = request.headers.get("X-Provider", "gemini")
    api_key = request.headers.get("X-API-Key")
    model = request.headers.get("X-Model")

    try:
        result = ChatService.send_message(
            message=user_text,
            session_id=session_id,
            provider_name=provider_name,
            api_key=api_key,
            model=model,
            client_ip=request.META.get("REMOTE_ADDR", "unknown"),
            _rate_limiter=allow,
            _provider_factory=get_provider,
            _retriever=retrieve_relevant_chunks,
        )
        return JsonResponse(
            {"response": result["response"], "sources": result["sources"]}
        )
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except ProviderAuthError as e:
        return JsonResponse({"error": str(e)}, status=401)
    except RateLimitExceeded as e:
        return JsonResponse({"error": str(e)}, status=429)
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

    ChatService.clear_history(session_id)
    return JsonResponse({"status": "cleared"})
