# orders/permissions.py
from rest_framework import permissions

class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow owners of an order
    to edit/delete it. Admins/staff can do anything.
    """

    def has_object_permission(self, request, view, obj):
        # Safe methods (GET, HEAD, OPTIONS) are always allowed
        if request.method in permissions.SAFE_METHODS:
            return True

        # Staff/admins can do anything
        if request.user and request.user.is_staff:
            return True

        # Otherwise only the owner can update/delete
        return obj.user == request.user
