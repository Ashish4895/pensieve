import sys

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Dev-only helper: document/run celery with autoreload (never in production)"

    def handle(self, *args, **options):
        if not settings.DEBUG:
            self.stderr.write("reload_celery is only allowed when DEBUG=true")
            sys.exit(1)
        self.stdout.write(
            "Run: celery -A pensieve worker --loglevel=INFO --pool=solo\n"
            "Use process manager autoreload in development only; never in production."
        )
