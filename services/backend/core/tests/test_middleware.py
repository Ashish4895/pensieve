import uuid

import pytest
from django.test import Client


@pytest.mark.django_db
def test_request_id_middleware_generates_header():
    response = Client().get("/api/docs/")

    assert response.status_code == 200
    request_id = response.headers.get("X-Request-ID")
    assert request_id
    uuid.UUID(request_id)


@pytest.mark.django_db
def test_request_id_middleware_echoes_client_header():
    client = Client()
    response = client.get("/api/docs/", HTTP_X_REQUEST_ID="client-request-42")

    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == "client-request-42"
