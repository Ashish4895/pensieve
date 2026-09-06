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
