from django.urls import path

from notifications.views import (
    NotificationListView,
    NotificationMarkReadView,
    NotificationStreamView,
)


urlpatterns = [
    path("", NotificationListView.as_view(), name="notification-list"),
    path("stream/", NotificationStreamView.as_view(), name="notification-stream"),
    path(
        "<int:notification_id>/read/",
        NotificationMarkReadView.as_view(),
        name="notification-mark-read",
    ),
]
