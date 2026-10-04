from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.status import HTTP_201_CREATED, HTTP_204_NO_CONTENT
from rest_framework.views import APIView

from core.api import api_error, api_success
from tools.models import McpServer, ToolDefinition, UserToolPreference
from tools.permissions import CanManageBuiltinCatalog, CanManageMcpServers
from tools.serializers import (
    McpServerSerializer,
    ToolCatalogFlagSerializer,
    ToolDefinitionSerializer,
    ToolPreferenceSerializer,
)
from tools.services.registry import discover_mcp_tools


class McpServerListCreateView(APIView):
    permission_classes = [IsAuthenticated, CanManageMcpServers]

    @extend_schema(responses=McpServerSerializer(many=True))
    def get(self, request):
        servers = McpServer.objects.all()
        return api_success(
            {"results": McpServerSerializer(servers, many=True).data}
        )

    @extend_schema(request=McpServerSerializer, responses=McpServerSerializer)
    def post(self, request):
        serializer = McpServerSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        server = serializer.save(is_builtin=False)
        return api_success(
            McpServerSerializer(server).data,
            message="Created",
            status_code=HTTP_201_CREATED,
        )


class McpServerDetailView(APIView):
    permission_classes = [IsAuthenticated, CanManageMcpServers]

    def get_object(self, server_id):
        return get_object_or_404(McpServer, pk=server_id)

    def patch(self, request, server_id):
        server = self.get_object(server_id)
        if server.is_builtin and not CanManageBuiltinCatalog().has_permission(
            request, self
        ):
            return api_error(
                message="Only super_admin can modify the builtin server",
                status_code=403,
            )
        serializer = McpServerSerializer(
            server,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        server = serializer.save()
        return api_success(McpServerSerializer(server).data)

    def delete(self, request, server_id):
        server = self.get_object(server_id)
        if server.is_builtin:
            return api_error(
                message="Cannot delete builtin MCP server", status_code=400
            )
        server.delete()
        return api_success(None, message="Deleted", status_code=HTTP_204_NO_CONTENT)


class McpServerDiscoverView(APIView):
    permission_classes = [IsAuthenticated, CanManageMcpServers]

    def post(self, request, server_id):
        server = get_object_or_404(McpServer, pk=server_id)
        try:
            tools = discover_mcp_tools(server)
        except Exception as exc:
            return api_error(message=f"Discover failed: {exc}", status_code=502)
        return api_success(
            {
                "count": len(tools),
                "tools": ToolDefinitionSerializer(tools, many=True).data,
            },
            message="Discovered",
        )


class ToolListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tools = ToolDefinition.objects.filter(
            enabled=True,
            mcp_server__enabled=True,
        ).select_related("mcp_server")
        prefs = {
            p.tool_id: p.enabled
            for p in UserToolPreference.objects.filter(user=request.user)
        }
        return api_success(
            {
                "results": ToolDefinitionSerializer(
                    tools,
                    many=True,
                    context={"prefs": prefs},
                ).data
            }
        )


class ToolPreferenceView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, tool_id):
        tool = get_object_or_404(
            ToolDefinition,
            pk=tool_id,
            enabled=True,
            mcp_server__enabled=True,
        )
        serializer = ToolPreferenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pref, _ = UserToolPreference.objects.update_or_create(
            user=request.user,
            tool=tool,
            defaults={"enabled": serializer.validated_data["enabled"]},
        )
        return api_success({"tool_id": tool.id, "enabled": pref.enabled})


class ToolCatalogFlagView(APIView):
    permission_classes = [IsAuthenticated, CanManageBuiltinCatalog]

    def patch(self, request, tool_id):
        tool = get_object_or_404(ToolDefinition, pk=tool_id)
        serializer = ToolCatalogFlagSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tool.enabled = serializer.validated_data["enabled"]
        tool.save(update_fields=["enabled", "updated_at"])
        return api_success(ToolDefinitionSerializer(tool).data)
