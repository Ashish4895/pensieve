from django.conf import settings
from django.db import models


class McpServer(models.Model):
    class Transport(models.TextChoices):
        STDIO = "stdio", "stdio"

    name = models.CharField(max_length=128, unique=True)
    transport = models.CharField(
        max_length=32,
        choices=Transport,
        default=Transport.STDIO,
    )
    command = models.CharField(max_length=512, blank=True, default="")
    args = models.JSONField(default=list, blank=True)
    env_ciphertext = models.TextField(blank=True, default="")
    enabled = models.BooleanField(default=True)
    is_builtin = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="mcp_servers",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ToolDefinition(models.Model):
    mcp_server = models.ForeignKey(
        McpServer,
        on_delete=models.CASCADE,
        related_name="tools",
    )
    name = models.CharField(max_length=128)
    title = models.CharField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True, default="")
    input_schema = models.JSONField(default=dict, blank=True)
    annotations = models.JSONField(default=dict, blank=True)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=("mcp_server", "name"),
                name="unique_tool_per_server",
            ),
        ]

    def __str__(self):
        return f"{self.mcp_server.name}:{self.name}"


class UserToolPreference(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tool_preferences",
    )
    tool = models.ForeignKey(
        ToolDefinition,
        on_delete=models.CASCADE,
        related_name="user_preferences",
    )
    enabled = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("user", "tool"),
                name="unique_user_tool_preference",
            ),
        ]
