import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from notifications.models import Notification


@pytest.mark.django_db
def test_list_and_mark_read_are_user_scoped():
    User = get_user_model()
    a = User.objects.create_user(email="a@ex.com", password="StrongPass123!")
    b = User.objects.create_user(email="b@ex.com", password="StrongPass123!")
    Notification.objects.create(user=a, title="A1", body="x", kind="ingest")
    Notification.objects.create(user=b, title="B1", body="y", kind="ingest")
    Notification.objects.create(user=a, title="A2", body="z", kind="info")

    client = APIClient()
    client.force_authenticate(user=a)
    listed = client.get("/api/v1/notifications/")

    assert listed.status_code == 200
    assert listed.data["success"] is True
    assert [item["title"] for item in listed.data["data"]["results"]] == [
        "A2",
        "A1",
    ]

    notification_id = listed.data["data"]["results"][0]["id"]
    marked = client.post(f"/api/v1/notifications/{notification_id}/read/")

    assert marked.status_code == 200
    assert marked.data["data"]["read_at"] is not None


@pytest.mark.django_db
def test_mark_read_returns_not_found_for_another_users_notification():
    User = get_user_model()
    owner = User.objects.create_user(
        email="owner@ex.com", password="StrongPass123!"
    )
    other = User.objects.create_user(
        email="other@ex.com", password="StrongPass123!"
    )
    notification = Notification.objects.create(user=owner, title="Private")

    client = APIClient()
    client.force_authenticate(user=other)
    response = client.post(f"/api/v1/notifications/{notification.pk}/read/")

    assert response.status_code == 404
    assert response.data["success"] is False
    notification.refresh_from_db()
    assert notification.read_at is None
