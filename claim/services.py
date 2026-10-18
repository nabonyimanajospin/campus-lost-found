"""Claim/item state transitions. Each runs atomically and locks the rows involved."""
from django.db import transaction
from django.utils import timezone

from item.models import Item

from .models import Claim


class ClaimStateError(Exception):
    """The requested transition is not allowed from the current state."""


def _lock(claim_id):
    claim = Claim.objects.select_for_update().get(pk=claim_id)
    item = Item.objects.select_for_update().get(pk=claim.item_id)
    return claim, item


@transaction.atomic
def approve_claim(claim):
    claim, item = _lock(claim.pk)
    if claim.status != Claim.Status.PENDING:
        raise ClaimStateError(f"Only pending claims can be approved (this one is {claim.status}).")
    if item.is_returned:
        raise ClaimStateError("This item has already been returned.")

    now = timezone.now()
    claim.status = Claim.Status.APPROVED
    claim.resolved_at = now
    claim.save()

    item.status = Item.Status.RETURNED
    item.save()

    # The item has a new home, so every other open claim is closed.
    Claim.objects.filter(item=item, status=Claim.Status.PENDING).exclude(pk=claim.pk).update(
        status=Claim.Status.REJECTED, resolved_at=now, updated_at=now
    )
    return claim


@transaction.atomic
def reject_claim(claim):
    claim, _ = _lock(claim.pk)
    if claim.status != Claim.Status.PENDING:
        raise ClaimStateError(f"Only pending claims can be rejected (this one is {claim.status}).")
    claim.status = Claim.Status.REJECTED
    claim.resolved_at = timezone.now()
    claim.save()
    return claim


@transaction.atomic
def withdraw_claim(claim):
    claim, _ = _lock(claim.pk)
    if claim.status != Claim.Status.PENDING:
        raise ClaimStateError(f"Only pending claims can be withdrawn (this one is {claim.status}).")
    claim.status = Claim.Status.WITHDRAWN
    claim.resolved_at = timezone.now()
    claim.save()
    return claim


@transaction.atomic
def mark_item_returned(item):
    """Owner closes the case without a claim (e.g. handed it over in person)."""
    item = Item.objects.select_for_update().get(pk=item.pk)
    if item.is_returned:
        raise ClaimStateError("This item has already been returned.")
    now = timezone.now()
    item.status = Item.Status.RETURNED
    item.save()
    Claim.objects.filter(item=item, status=Claim.Status.PENDING).update(
        status=Claim.Status.REJECTED, resolved_at=now, updated_at=now
    )
    return item
