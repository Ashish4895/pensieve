from django.urls import path

from chatbot.api_views import (
    ChatClearView,
    ChatHistoryView,
    ChatSendView,
    IngestEnqueueView,
)

urlpatterns = [
    path("chat/", ChatSendView.as_view(), name="chat-send"),
    path("chat/history/", ChatHistoryView.as_view(), name="chat-history"),
    path("chat/clear/", ChatClearView.as_view(), name="chat-clear"),
    path("ingest/", IngestEnqueueView.as_view(), name="ingest-enqueue"),
]
