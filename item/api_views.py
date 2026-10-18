from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response

from claim.services import ClaimStateError, mark_item_returned
from claim.api_errors import Conflict
from student.permissions import HasStudentProfile

from .models import Item
from .serializers import ItemSerializer


class IsItemOwnerOrStaff(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user.is_staff or obj.created_by.user_id == request.user.id


class ItemViewSet(viewsets.ModelViewSet):
    """
    Browse is public. Posting needs a student account; editing/closing is owner (or staff) only.

    Query params: ?status=lost|found|returned  ?category=<id>  ?mine=true  ?search=<text>
                  ?ordering=created_at|-created_at
    """

    serializer_class = ItemSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "description", "location"]
    ordering_fields = ["created_at", "updated_at", "title"]

    def get_queryset(self):
        qs = Item.objects.select_related("created_by", "category")
        params = self.request.query_params
        if params.get("status") in Item.Status.values:
            qs = qs.filter(status=params["status"])
        if params.get("category", "").isdigit():
            qs = qs.filter(category_id=params["category"])
        if params.get("mine", "").lower() in ("1", "true", "yes"):
            user = self.request.user
            qs = qs.filter(created_by__user=user) if user.is_authenticated else qs.none()
        return qs

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return []
        if self.action == "create":
            return [IsAuthenticated(), HasStudentProfile()]
        return [IsAuthenticated(), IsItemOwnerOrStaff()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user.student)

    def _ensure_editable(self, item):
        if item.is_returned and not self.request.user.is_staff:
            raise ValidationError("Returned items are closed and can no longer be changed or deleted.")

    def perform_update(self, serializer):
        self._ensure_editable(serializer.instance)
        serializer.save()

    def perform_destroy(self, instance):
        self._ensure_editable(instance)
        instance.delete()

    @action(detail=True, methods=["post"], url_path="mark-returned")
    def mark_returned(self, request, pk=None):
        item = self.get_object()
        try:
            item = mark_item_returned(item)
        except ClaimStateError as exc:
            raise Conflict(str(exc))
        return Response(self.get_serializer(item).data)
