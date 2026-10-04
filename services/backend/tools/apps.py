from django.apps import AppConfig


class ToolsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tools"

    def ready(self):
        from django.db.models.signals import post_migrate

        from tools.services.registry import ensure_builtin_server

        post_migrate.connect(ensure_builtin_server, sender=self)
