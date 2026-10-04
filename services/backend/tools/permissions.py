from rest_framework.permissions import BasePermission

from accounts.models import User


class CanManageMcpServers(BasePermission):
    """admin or super_admin may CRUD MCP server connections."""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in {
            User.Role.ADMIN,
            User.Role.SUPER_ADMIN,
        }


class CanManageBuiltinCatalog(BasePermission):
    """Only super_admin may toggle builtin / first-party catalog flags."""

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == User.Role.SUPER_ADMIN
        )
