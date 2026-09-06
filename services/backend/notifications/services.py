import asyncio
import json

from asgiref.sync import sync_to_async
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone

from notifications.models import Notification
from notifications.serializers import NotificationSerializer


def create_notification(
    *,
    user,
    title: str,
    body: str = "",
    kind: str = "info",
) -> Notification:
    return Notification.objects.create(
        user=user,
        title=title,
        body=body,
        kind=kind,
    )


def _fetch_notifications(user, last_event_id):
    return list(
        Notification.objects.filter(
            user=user,
            id__gt=last_event_id,
        ).order_by("id")
    )


async def iter_sse_events(
    user,
    last_event_id: int = 0,
    *,
    max_rounds: int | None = None,
    sleep_fn=asyncio.sleep,
    heartbeat_every: int = 15,
):
    rounds = 0
    while max_rounds is None or rounds < max_rounds:
        notifications = await sync_to_async(_fetch_notifications)(
            user,
            last_event_id,
        )
        for notification in notifications:
            data = json.dumps(
                NotificationSerializer(notification).data,
                cls=DjangoJSONEncoder,
            )
            yield (
                f"id: {notification.id}\n"
                "event: notification\n"
                f"data: {data}\n\n"
            )
            last_event_id = notification.id

        rounds += 1
        await sleep_fn(1)
        if heartbeat_every and rounds % heartbeat_every == 0:
            yield ": heartbeat\n\n"


def mark_notification_read(notification):
    if notification.read_at is None:
        notification.read_at = timezone.now()
        notification.save(update_fields=["read_at"])
    return notification
