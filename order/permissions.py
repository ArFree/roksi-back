from rest_framework.permissions import BasePermission


class OrdersPermission(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.method == "POST" or request.user.is_authenticated
        )
