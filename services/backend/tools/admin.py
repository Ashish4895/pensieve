from django.contrib import admin

from tools.models import McpServer, ToolDefinition, UserToolPreference


@admin.register(McpServer)
class McpServerAdmin(admin.ModelAdmin):
    list_display = ("name", "transport", "enabled", "is_builtin", "updated_at")
    list_filter = ("enabled", "is_builtin", "transport")
    search_fields = ("name",)


@admin.register(ToolDefinition)
class ToolDefinitionAdmin(admin.ModelAdmin):
    list_display = ("name", "mcp_server", "enabled", "updated_at")
    list_filter = ("enabled", "mcp_server")
    search_fields = ("name", "title")


@admin.register(UserToolPreference)
class UserToolPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "tool", "enabled")
    list_filter = ("enabled",)
