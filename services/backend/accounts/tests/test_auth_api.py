import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_refresh_without_cookies_returns_401_not_csrf_403():
    client = APIClient(enforce_csrf_checks=True)
    response = client.post("/api/v1/auth/refresh/", {}, format="json")
    assert response.status_code == 401
    assert response.data["success"] is False


@pytest.mark.django_db
def test_jwt_auth_flow_uses_refresh_cookie_and_access_body():
    client = APIClient(enforce_csrf_checks=True)
    credentials = {"email": "user@example.com", "password": "StrongPass123!"}

    register = client.post("/api/v1/auth/register/", credentials, format="json")

    assert register.status_code == 201
    assert register.data["success"] is True
    assert register.data["data"]["access"]
    assert register.data["data"]["user"] == {
        "id": register.data["data"]["user"]["id"],
        "email": credentials["email"],
        "role": "user",
    }
    assert "refresh" not in register.data["data"]
    assert register.cookies["refresh"]["httponly"] is True
    assert register.cookies["refresh"]["path"] == "/api/v1/auth/"
    csrf_token = register.cookies["csrftoken"].value

    access = register.data["data"]["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    me = client.get("/api/v1/auth/me/")
    assert me.status_code == 200
    assert me.data["data"]["email"] == credentials["email"]

    client.credentials()
    login = client.post("/api/v1/auth/login/", credentials, format="json")
    assert login.status_code == 200
    assert login.data["data"]["access"]
    assert login.cookies["refresh"]["httponly"] is True

    blocked_refresh = client.post("/api/v1/auth/refresh/", {}, format="json")
    assert blocked_refresh.status_code == 403

    refresh = client.post(
        "/api/v1/auth/refresh/",
        {},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert refresh.status_code == 200
    assert refresh.data["data"]["access"]
    assert refresh.cookies["refresh"]["httponly"] is True

    blocked_logout = client.post("/api/v1/auth/logout/", {}, format="json")
    assert blocked_logout.status_code == 403

    logout = client.post(
        "/api/v1/auth/logout/",
        {},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert logout.status_code == 200
    assert logout.cookies["refresh"].value == ""
    assert logout.cookies["refresh"]["path"] == "/api/v1/auth/"

    rejected_refresh = client.post(
        "/api/v1/auth/refresh/",
        {},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert rejected_refresh.status_code == 401
    assert rejected_refresh.data["success"] is False


@pytest.mark.django_db
def test_garbage_refresh_cookie_returns_401_envelope():
    client = APIClient(enforce_csrf_checks=True)
    register = client.post(
        "/api/v1/auth/register/",
        {"email": "invalid-token@example.com", "password": "StrongPass123!"},
        format="json",
    )
    csrf_token = register.cookies["csrftoken"].value
    client.cookies["refresh"] = "not-a-jwt"

    response = client.post(
        "/api/v1/auth/refresh/",
        {},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 401
    assert response.data["success"] is False
    assert response.data["message"]
    assert response.data["data"] is None
    assert response.data["errors"]["detail"]
