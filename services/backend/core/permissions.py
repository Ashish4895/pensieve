from rest_framework.permissions import BasePermission

from accounts.models import User


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == User.Role.ADMIN
        )


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == User.Role.SUPER_ADMIN
        )


def HasRole(role):
    class _HasRole(BasePermission):
        def has_permission(self, request, view):
            return (
                request.user.is_authenticated
                and request.user.role == role
            )

    return _HasRole
