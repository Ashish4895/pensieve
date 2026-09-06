from django.urls import path

from notifications.views import NotificationListView, NotificationMarkReadView


urlpatterns = [
    path("", NotificationListView.as_view(), name="notification-list"),
    path(
        "<int:notification_id>/read/",
        NotificationMarkReadView.as_view(),
        name="notification-mark-read",
    ),
]
