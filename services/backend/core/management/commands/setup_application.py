import os

from django.contrib.auth import get_user_model
from django.core.management import BaseCommand, CommandError, call_command


class Command(BaseCommand):
    help = "Apply migrations and optionally bootstrap a super admin."

    def handle(self, *args, **options):
        call_command("migrate", interactive=False)

        email = os.environ.get("PENSIVE_BOOTSTRAP_EMAIL")
        password = os.environ.get("PENSIVE_BOOTSTRAP_PASSWORD")
        if not email and not password:
            self.stdout.write(self.style.SUCCESS("Application setup complete."))
            return
        if not email or not password:
            raise CommandError(
                "PENSIVE_BOOTSTRAP_EMAIL and PENSIVE_BOOTSTRAP_PASSWORD must both be set."
            )

        user_model = get_user_model()
        email = user_model.objects.normalize_email(email)
        user, created = user_model.objects.get_or_create(email=email)
        user.role = user_model.Role.SUPER_ADMIN
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save(update_fields=("role", "is_staff", "is_superuser", "password"))

        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} super admin {email}."))
        self.stdout.write(self.style.SUCCESS("Application setup complete."))
