from django.urls import path

from realtime.consumers import ChatPingConsumer

websocket_urlpatterns = [
    path("ws/v1/chat/", ChatPingConsumer.as_asgi()),
]
