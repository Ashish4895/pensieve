from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient


@pytest.mark.django_db
@patch("chatbot.api_views.run_ingest")
def test_enqueue_ingest_requires_auth_and_returns_task_id(mock_task):
    mock_task.delay.return_value = MagicMock(id="abc-123")
    client = APIClient()

    assert client.post("/api/v1/ingest/").status_code == 401

    user = get_user_model().objects.create_user(
        email="a@b.com",
        password="StrongPass123!",
    )
    client.force_authenticate(user=user)
    response = client.post(
        "/api/v1/ingest/",
        {"directory": "documents"},
        format="json",
    )

    assert response.status_code == 202
    assert response.data["success"] is True
    assert response.data["data"]["task_id"] == "abc-123"
    mock_task.delay.assert_called_once_with("documents")


@pytest.mark.django_db
@pytest.mark.parametrize("directory", ["/etc", "../secret"])
@patch("chatbot.api_views.run_ingest")
def test_enqueue_ingest_rejects_unsafe_directory(mock_task, directory):
    user = get_user_model().objects.create_user(
        email="unsafe@b.com",
        password="StrongPass123!",
    )
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        "/api/v1/ingest/",
        {"directory": directory},
        format="json",
    )

    assert response.status_code == 400
    assert response.data["success"] is False
    mock_task.delay.assert_not_called()
