import asyncio
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.http import StreamingHttpResponse
from rest_framework.test import APIClient

from accounts.services import AuthService
from notifications.models import Notification
from notifications.services import iter_sse_events


async def _collect(async_iterable):
    return [chunk async for chunk in async_iterable]


async def _no_sleep(_):
    return None


@pytest.mark.django_db(transaction=True)
def test_iter_sse_events_emits_notification_and_heartbeat():
    user = get_user_model().objects.create_user(
        email="sse@ex.com",
        password="StrongPass123!",
    )
    notification = Notification.objects.create(
        user=user,
        title="Hi",
        body="b",
        kind="info",
    )
    sleeps = []

    async def record_sleep(seconds):
        sleeps.append(seconds)

    chunks = asyncio.run(
        _collect(
            iter_sse_events(
                user,
                max_rounds=2,
                sleep_fn=record_sleep,
                heartbeat_every=1,
            )
        )
    )

    joined = "".join(chunks)
    assert f"id: {notification.id}" in joined
    assert "event: notification" in joined
    assert '"title": "Hi"' in joined
    assert ": heartbeat" in joined
    assert sleeps == [1, 1]


@pytest.mark.django_db(transaction=True)
def test_iter_sse_events_is_user_scoped_and_resumes_after_last_event():
    User = get_user_model()
    user = User.objects.create_user(
        email="owner@ex.com",
        password="StrongPass123!",
    )
    other = User.objects.create_user(
        email="other@ex.com",
        password="StrongPass123!",
    )
    previous = Notification.objects.create(user=user, title="Previous")
    current = Notification.objects.create(user=user, title="Current")
    Notification.objects.create(user=other, title="Private")

    joined = "".join(
        asyncio.run(
            _collect(
                iter_sse_events(
                    user,
                    last_event_id=previous.id,
                    max_rounds=1,
                    sleep_fn=_no_sleep,
                )
            )
        )
    )

    assert f"id: {previous.id}" not in joined
    assert f"id: {current.id}" in joined
    assert '"title": "Private"' not in joined


@pytest.mark.django_db(transaction=True)
def test_streaming_response_consumes_sse_as_async_iterator():
    user = get_user_model().objects.create_user(
        email="asgi@ex.com",
        password="StrongPass123!",
    )
    notification = Notification.objects.create(user=user, title="ASGI")
    response = StreamingHttpResponse(
        iter_sse_events(
            user,
            max_rounds=1,
            sleep_fn=_no_sleep,
        ),
        content_type="text/event-stream",
    )

    async def next_chunk():
        iterator = response.__aiter__()
        return await iterator.__anext__()

    chunk = asyncio.run(next_chunk())
    assert f"id: {notification.id}".encode() in chunk


@pytest.mark.django_db
def test_stream_requires_authentication():
    response = APIClient().get("/api/v1/notifications/stream/")

    assert response.status_code == 401


@pytest.mark.django_db
@patch("notifications.views.iter_sse_events")
def test_stream_accepts_access_token_query_parameter(mock_events):
    async def events():
        yield ": heartbeat\n\n"

    mock_events.return_value = events()
    user = get_user_model().objects.create_user(
        email="query-token@ex.com",
        password="StrongPass123!",
    )
    access = AuthService.issue_tokens(user)["access"]

    response = APIClient().get(
        "/api/v1/notifications/stream/",
        {"access": access},
        HTTP_ACCEPT="text/event-stream",
    )

    assert response.status_code == 200
    mock_events.assert_called_once_with(user, 0, max_rounds=300)


@pytest.mark.django_db
@patch("notifications.views.iter_sse_events")
def test_stream_uses_last_event_id_and_sse_headers(mock_events):
    async def events():
        yield ": heartbeat\n\n"

    mock_events.return_value = events()
    user = get_user_model().objects.create_user(
        email="stream@ex.com",
        password="StrongPass123!",
    )
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get(
        "/api/v1/notifications/stream/",
        HTTP_LAST_EVENT_ID="12",
    )

    assert response.status_code == 200
    assert response["Content-Type"] == "text/event-stream"
    assert response["Cache-Control"] == "no-cache"
    assert response["X-Accel-Buffering"] == "no"
    assert b"".join(asyncio.run(_collect(response.streaming_content))) == b": heartbeat\n\n"
    mock_events.assert_called_once_with(user, 12, max_rounds=300)
