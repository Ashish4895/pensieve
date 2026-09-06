import pytest
from django.contrib.auth import get_user_model


@pytest.mark.django_db
def test_user_default_role_is_user():
    user = get_user_model().objects.create_user(email="user@example.com")

    assert user.role == "user"
