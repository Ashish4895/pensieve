from django.urls import path

from tools.views import (
    McpServerDetailView,
    McpServerDiscoverView,
    McpServerListCreateView,
    ToolCatalogFlagView,
    ToolListView,
    ToolPreferenceView,
)

urlpatterns = [
    path("servers/", McpServerListCreateView.as_view(), name="mcp-server-list"),
    path(
        "servers/<int:server_id>/",
        McpServerDetailView.as_view(),
        name="mcp-server-detail",
    ),
    path(
        "servers/<int:server_id>/discover/",
        McpServerDiscoverView.as_view(),
        name="mcp-server-discover",
    ),
    path("", ToolListView.as_view(), name="tool-list"),
    path(
        "<int:tool_id>/preference/",
        ToolPreferenceView.as_view(),
        name="tool-preference",
    ),
    path(
        "<int:tool_id>/catalog/",
        ToolCatalogFlagView.as_view(),
        name="tool-catalog-flag",
    ),
]
