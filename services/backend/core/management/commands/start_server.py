import os

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Start ASGI server with uvicorn"

    def handle(self, *args, **options):
        import uvicorn

        port = int(os.environ.get("PORT", "8000"))
        uvicorn.run("pensieve.asgi:application", host="0.0.0.0", port=port, reload=False)
