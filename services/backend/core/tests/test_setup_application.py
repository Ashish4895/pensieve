from unittest.mock import MagicMock

from django.core.management import call_command


def test_setup_application_bootstraps_super_admin_idempotently(monkeypatch):
    monkeypatch.setenv("PENSIVE_BOOTSTRAP_EMAIL", "Admin@Example.com")
    monkeypatch.setenv("PENSIVE_BOOTSTRAP_PASSWORD", "test-password")
    migrate = MagicMock()
    monkeypatch.setattr(
        "core.management.commands.setup_application.call_command",
        migrate,
    )
    user = MagicMock()
    user_model = MagicMock()
    user_model.Role.SUPER_ADMIN = "super_admin"
    user_model.objects.normalize_email.return_value = "Admin@example.com"
    user_model.objects.get_or_create.side_effect = [(user, True), (user, False)]
    monkeypatch.setattr(
        "core.management.commands.setup_application.get_user_model",
        lambda: user_model,
    )

    call_command("setup_application")
    call_command("setup_application")

    assert migrate.call_count == 2
    assert user_model.objects.get_or_create.call_count == 2
    assert user.role == "super_admin"
    assert user.is_staff is True
    assert user.is_superuser is True
    user.set_password.assert_called_with("test-password")
