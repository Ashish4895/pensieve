import uuid

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.status import HTTP_202_ACCEPTED
from rest_framework.views import APIView

from chatbot.providers.base import (
    ProviderAuthError,
    ProviderRequestError,
    UnsupportedProviderError,
)
from chatbot.services.chat import ChatService, RateLimitExceeded
from chatbot.tasks import run_ingest
from core.api import api_error, api_success
from core.permissions import IsAdmin, IsSuperAdmin


def _require_api_key(request):
    api_key = request.headers.get("X-API-Key")
    if not api_key or not api_key.strip():
        return None, api_error(message="API key required", status_code=401)
    return api_key, None


def _session_id(value, *, required=False):
    if value is None and not required:
        return str(uuid.uuid4())
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


class ChatSendView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        api_key, error = _require_api_key(request)
        if error:
            return error

        session_id = _session_id(request.data.get("session_id"))
        if session_id is None:
            return api_error(
                message="Invalid session ID",
                errors={"session_id": ["Must be a non-empty string."]},
            )

        try:
            result = ChatService.send_message(
                message=request.data.get("message"),
                session_id=session_id,
                provider_name=request.headers.get("X-Provider", "gemini"),
                api_key=api_key,
                model=request.headers.get("X-Model"),
                client_ip=request.META.get("REMOTE_ADDR", "unknown"),
                user=request.user,
            )
        except (ValueError, UnsupportedProviderError) as exc:
            return api_error(message=str(exc), status_code=400)
        except ProviderAuthError as exc:
            return api_error(message=str(exc), status_code=401)
        except RateLimitExceeded as exc:
            return api_error(message=str(exc), status_code=429)
        except ProviderRequestError as exc:
            return api_error(message=str(exc), status_code=502)

        return api_success(data=result)


class ChatHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        _, error = _require_api_key(request)
        if error:
            return error

        session_id = _session_id(
            request.query_params.get("session_id"),
            required=True,
        )
        if session_id is None:
            return api_error(
                message="Session ID required",
                errors={"session_id": ["This query parameter is required."]},
            )

        return api_success(
            data={
                "history": ChatService.get_history(session_id, user=request.user),
                "session_id": session_id,
            }
        )


class ChatClearView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        _, error = _require_api_key(request)
        if error:
            return error

        session_id = _session_id(request.data.get("session_id"), required=True)
        if session_id is None:
            return api_error(
                message="Session ID required",
                errors={"session_id": ["This field is required."]},
            )

        return api_success(
            data={
                "deleted": ChatService.clear_history(session_id, user=request.user),
                "session_id": session_id,
            }
        )


class IngestEnqueueView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin | IsSuperAdmin]
    throttle_scope = "ingest"

    def post(self, request):
        directory = request.data.get("directory") or "documents"
        if not isinstance(directory, str) or not directory.strip():
            directory = "documents"

        directory = directory.strip()
        if directory != "documents":
            return api_error(
                message="Invalid directory",
                errors={"directory": ["Only 'documents' is allowed."]},
                status_code=400,
            )

        async_result = run_ingest.delay(directory, request.user.id)
        return api_success(
            data={"task_id": async_result.id},
            message="Ingest enqueued",
            status_code=HTTP_202_ACCEPTED,
        )
