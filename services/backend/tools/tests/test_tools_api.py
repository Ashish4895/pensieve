import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from tools.crypto import decrypt_env, encrypt_env
from tools.models import McpServer, ToolDefinition, UserToolPreference
from tools.services.registry import ensure_builtin_server, tools_for_user

User = get_user_model()


@pytest.fixture
def api():
    return APIClient()


def _auth(client, *, email, password="StrongPass123!", role="user"):
    user = User.objects.create_user(email=email, password=password, role=role)
    login = client.post(
        "/api/v1/auth/login/",
        {"email": email, "password": password},
        format="json",
    )
    assert login.status_code == 200
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['data']['access']}")
    return user


@pytest.mark.django_db
def test_encrypt_env_roundtrip():
    cipher = encrypt_env({"TOKEN": "secret"})
    assert "secret" not in cipher
    assert decrypt_env(cipher) == {"TOKEN": "secret"}


@pytest.mark.django_db
def test_user_cannot_list_servers(api):
    _auth(api, email="user@example.com", role=User.Role.USER)
    response = api.get("/api/v1/tools/servers/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_admin_can_create_server_without_leaking_env(api):
    _auth(api, email="admin@example.com", role=User.Role.ADMIN)
    response = api.post(
        "/api/v1/tools/servers/",
        {
            "name": "weather",
            "command": "uv",
            "args": ["run", "weather.py"],
            "env": {"API_KEY": "shh"},
        },
        format="json",
    )
    assert response.status_code == 201
    data = response.data["data"]
    assert data["name"] == "weather"
    assert data["has_env"] is True
    assert "env" not in data
    assert "shh" not in str(response.data)
    server = McpServer.objects.get(name="weather")
    assert decrypt_env(server.env_ciphertext)["API_KEY"] == "shh"


@pytest.mark.django_db
def test_cannot_delete_builtin_server(api):
    ensure_builtin_server()
    _auth(api, email="admin@example.com", role=User.Role.ADMIN)
    builtin = McpServer.objects.get(is_builtin=True)
    response = api.delete(f"/api/v1/tools/servers/{builtin.id}/")
    assert response.status_code == 400


@pytest.mark.django_db
def test_tool_preference_filters_chat_tools(api):
    user = _auth(api, email="user@example.com", role=User.Role.USER)
    server = ensure_builtin_server()
    tool = ToolDefinition.objects.create(
        mcp_server=server,
        name="pensieve_search_documents",
        title="Search",
        enabled=True,
    )
    assert [t.name for t in tools_for_user(user)] == ["pensieve_search_documents"]

    response = api.patch(
        f"/api/v1/tools/{tool.id}/preference/",
        {"enabled": False},
        format="json",
    )
    assert response.status_code == 200
    assert tools_for_user(user) == []


@pytest.mark.django_db
def test_super_admin_can_disable_catalog_tool(api):
    ensure_builtin_server()
    server = McpServer.objects.get(is_builtin=True)
    tool = ToolDefinition.objects.create(
        mcp_server=server,
        name="pensieve_search_documents",
        enabled=True,
    )
    _auth(api, email="root@example.com", role=User.Role.SUPER_ADMIN)
    response = api.patch(
        f"/api/v1/tools/{tool.id}/catalog/",
        {"enabled": False},
        format="json",
    )
    assert response.status_code == 200
    tool.refresh_from_db()
    assert tool.enabled is False


@pytest.mark.django_db
def test_list_tools_includes_preference(api):
    user = _auth(api, email="user@example.com", role=User.Role.USER)
    server = ensure_builtin_server()
    tool = ToolDefinition.objects.create(
        mcp_server=server,
        name="pensieve_search_documents",
        title="Search",
        enabled=True,
    )
    UserToolPreference.objects.create(user=user, tool=tool, enabled=False)
    response = api.get("/api/v1/tools/")
    assert response.status_code == 200
    row = response.data["data"]["results"][0]
    assert row["preference_enabled"] is False
