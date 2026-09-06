from unittest.mock import patch

import pytest
from django.test import override_settings


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
@patch(
    "chatbot.tasks.ingest_documents",
    return_value={"files": 1, "chunks": 2, "cleared": True},
)
def test_run_ingest_task_calls_service(mock_ingest):
    from chatbot.tasks import run_ingest

    result = run_ingest.delay("documents").get()

    mock_ingest.assert_called_once_with("documents")
    assert result == {"files": 1, "chunks": 2, "cleared": True}


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
@patch(
    "chatbot.tasks.ingest_documents",
    return_value={"files": 1, "chunks": 2, "cleared": True},
)
def test_run_ingest_task_notifies_requesting_user(mock_ingest):
    from django.contrib.auth import get_user_model

    from chatbot.tasks import run_ingest
    from notifications.models import Notification

    user = get_user_model().objects.create_user(
        email="ingest@ex.com",
        password="StrongPass123!",
    )

    run_ingest.delay("documents", user.id).get()

    notification = Notification.objects.get(user=user)
    assert notification.title == "Ingest complete"
    assert notification.body == "files=1 chunks=2"
    assert notification.kind == "ingest"
