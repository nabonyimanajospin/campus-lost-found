from django.db import IntegrityError
from django.db.models import Q
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response

from student.permissions import HasStudentProfile

from . import services
from .api_errors import Conflict
from .models import Claim
from .serializers import ClaimSerializer


class IsItemOwnerOrStaff(BasePermission):
    def has_object_permission(self, request, view, claim):
        return request.user.is_staff or claim.item.created_by.user_id == request.user.id


class IsClaimant(BasePermission):
    def has_object_permission(self, request, view, claim):
        return claim.claimant.user_id == request.user.id


class ClaimViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    Claims are private: only the claimant, the item's owner and staff can see them.
    State changes go through approve / reject / withdraw so the rules can't be bypassed.

    Query params: ?item=<id>  ?status=pending|approved|rejected|withdrawn
                  ?role=claimant (my claims) | owner (claims on my items)
    """

    serializer_class = ClaimSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Claim.objects.select_related("item", "claimant", "item__created_by")
        if not user.is_staff:
            qs = qs.filter(Q(claimant__user=user) | Q(item__created_by__user=user))

        params = self.request.query_params
        if params.get("item", "").isdigit():
            qs = qs.filter(item_id=params["item"])
        if params.get("status") in Claim.Status.values:
            qs = qs.filter(status=params["status"])
        if params.get("role") == "claimant":
            qs = qs.filter(claimant__user=user)
        elif params.get("role") == "owner":
            qs = qs.filter(item__created_by__user=user)
        return qs

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), HasStudentProfile()]
        if self.action in ("approve", "reject"):
            return [IsAuthenticated(), IsItemOwnerOrStaff()]
        if self.action == "withdraw":
            return [IsAuthenticated(), IsClaimant()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        try:
            serializer.save(claimant=self.request.user.student)
        except IntegrityError:
            # Lost a race against a concurrent request; the DB constraints are the last line of defence.
            raise ValidationError({"item": "You already have an active claim on this item."})

    def _transition(self, fn):
        claim = self.get_object()
        try:
            claim = fn(claim)
        except services.ClaimStateError as exc:
            raise Conflict(str(exc))
        claim = self.get_queryset().get(pk=claim.pk)
        return Response(self.get_serializer(claim).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        return self._transition(services.approve_claim)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return self._transition(services.reject_claim)

    @action(detail=True, methods=["post"])
    def withdraw(self, request, pk=None):
        return self._transition(services.withdraw_claim)
