import pytest
from django.contrib.auth import get_user_model
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory, force_authenticate

from core.permissions import HasRole, IsAdmin, IsSuperAdmin

User = get_user_model()
factory = APIRequestFactory()


def _request_for(user=None):
    django_request = factory.get("/")
    if user is not None:
        force_authenticate(django_request, user=user)
    return Request(django_request)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("role", "expected"),
    [
        (User.Role.ADMIN, True),
        (User.Role.USER, False),
        (User.Role.SUPER_ADMIN, False),
    ],
)
def test_is_admin(role, expected):
    user = get_user_model().objects.create_user(
        email=f"{role}@example.com",
        role=role,
    )
    request = _request_for(user)

    assert IsAdmin().has_permission(request, None) is expected


@pytest.mark.django_db
def test_is_admin_denies_anonymous():
    request = _request_for()

    assert IsAdmin().has_permission(request, None) is False


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("role", "expected"),
    [
        (User.Role.SUPER_ADMIN, True),
        (User.Role.ADMIN, False),
        (User.Role.USER, False),
    ],
)
def test_is_super_admin(role, expected):
    user = get_user_model().objects.create_user(
        email=f"{role}-super@example.com",
        role=role,
    )
    request = _request_for(user)

    assert IsSuperAdmin().has_permission(request, None) is expected


@pytest.mark.django_db
def test_has_role_matches_required_role():
    user = get_user_model().objects.create_user(
        email="admin@example.com",
        role=User.Role.ADMIN,
    )
    request = _request_for(user)

    assert HasRole(User.Role.ADMIN)().has_permission(request, None) is True
    assert HasRole(User.Role.USER)().has_permission(request, None) is False
