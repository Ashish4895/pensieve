import pytest
from django.test import override_settings
from rest_framework.test import APIClient


@pytest.mark.django_db
@override_settings(
    CORS_ALLOWED_ORIGINS=["http://127.0.0.1:5173"],
    CORS_ALLOW_CREDENTIALS=True,
)
def test_cors_preflight_allows_spa_origin():
    client = APIClient()
    res = client.options(
        "/api/v1/auth/login/",
        HTTP_ORIGIN="http://127.0.0.1:5173",
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
    )
    assert res.status_code in (200, 204)
    assert res["Access-Control-Allow-Origin"] == "http://127.0.0.1:5173"
    assert res["Access-Control-Allow-Credentials"] == "true"
