from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import BaseRenderer, JSONRenderer
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from core.api import api_success
from notifications.models import Notification
from notifications.serializers import NotificationSerializer
from notifications.services import iter_sse_events, mark_notification_read


class EventStreamRenderer(BaseRenderer):
    """Accept EventSource's Accept: text/event-stream (DRF JSON-only → 406)."""

    media_type = "text/event-stream"
    format = "event-stream"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


class QueryParameterJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        authenticated = super().authenticate(request)
        if authenticated is not None:
            return authenticated

        raw_token = request.query_params.get("access", "").strip()
        if not raw_token:
            return None

        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token


class NotificationStreamView(APIView):
    authentication_classes = [QueryParameterJWTAuthentication]
    permission_classes = [IsAuthenticated]
    # EventSource sends Accept: text/event-stream; keep JSON for APIClient tests.
    renderer_classes = [EventStreamRenderer, JSONRenderer]

    def get(self, request):
        try:
            last_event_id = max(0, int(request.headers.get("Last-Event-ID", 0)))
        except (TypeError, ValueError):
            last_event_id = 0

        response = StreamingHttpResponse(
            iter_sse_events(request.user, last_event_id, max_rounds=300),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(user=request.user)
        return api_success(
            {"results": NotificationSerializer(notifications, many=True).data}
        )


class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, notification_id):
        notification = get_object_or_404(
            Notification,
            id=notification_id,
            user=request.user,
        )
        mark_notification_read(notification)
        return api_success(NotificationSerializer(notification).data)
