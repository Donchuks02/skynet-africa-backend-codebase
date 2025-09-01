from rest_framework.permissions import BasePermission


class IsServiceOwner(BasePermission):
    """
    Custom permission to ensure only the owner can manage a service.
    """

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user
