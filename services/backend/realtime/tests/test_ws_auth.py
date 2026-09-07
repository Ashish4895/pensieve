import pytest
from asgiref.sync import sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import override_settings

from accounts.services import AuthService
from pensieve.asgi import application

IN_MEMORY_CHANNELS = {
    "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
}


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@override_settings(CHANNEL_LAYERS=IN_MEMORY_CHANNELS)
async def test_ws_rejects_missing_token():
    communicator = WebsocketCommunicator(application, "/ws/v1/chat/")
    connected, code = await communicator.connect()
    assert connected is False
    assert code == 4401
    await communicator.wait()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@override_settings(CHANNEL_LAYERS=IN_MEMORY_CHANNELS)
async def test_ws_accepts_valid_token_and_pongs():
    user = await sync_to_async(get_user_model().objects.create_user)(
        email="ws@ex.com",
        password="StrongPass123!",
    )
    access = await sync_to_async(lambda: AuthService.issue_tokens(user)["access"])()

    communicator = WebsocketCommunicator(
        application,
        f"/ws/v1/chat/?token={access}",
    )
    connected, _ = await communicator.connect()
    assert connected is True

    await communicator.send_json_to({"type": "ping"})
    response = await communicator.receive_json_from()
    assert response == {"type": "pong"}
    await communicator.disconnect()
