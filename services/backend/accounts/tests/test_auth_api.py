import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_jwt_auth_flow_uses_refresh_cookie_and_access_body():
    client = APIClient()
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

    refresh = client.post("/api/v1/auth/refresh/", {}, format="json")
    assert refresh.status_code == 200
    assert refresh.data["data"]["access"]
    assert refresh.cookies["refresh"]["httponly"] is True

    logout = client.post("/api/v1/auth/logout/", {}, format="json")
    assert logout.status_code == 200
    assert logout.cookies["refresh"].value == ""
    assert logout.cookies["refresh"]["path"] == "/api/v1/auth/"

    rejected_refresh = client.post("/api/v1/auth/refresh/", {}, format="json")
    assert rejected_refresh.status_code == 401
    assert rejected_refresh.data["success"] is False
