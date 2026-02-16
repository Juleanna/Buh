from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """Дозвіл тільки для адміністраторів."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_admin


class IsAccountant(BasePermission):
    """Дозвіл для бухгалтерів та адміністраторів."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_admin or request.user.is_accountant


class IsInventoryManager(BasePermission):
    """Дозвіл для інвентаризаторів, бухгалтерів та адміністраторів."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return (
            request.user.is_admin
            or request.user.is_accountant
            or request.user.is_inventory_manager
        )
