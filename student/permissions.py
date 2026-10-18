from rest_framework import permissions


class HasStudentProfile(permissions.BasePermission):
    """Authenticated user that is linked to a Student record."""

    message = "Your account has no student profile."

    def has_permission(self, request, view):
        # hasattr is False when the reverse one-to-one does not exist.
        return bool(request.user and request.user.is_authenticated and hasattr(request.user, "student"))


class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)
