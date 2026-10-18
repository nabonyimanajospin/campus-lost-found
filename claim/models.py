from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from item.models import Item
from student.models import Student


class Claim(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        WITHDRAWN = "withdrawn", "Withdrawn"

    ACTIVE_STATUSES = (Status.PENDING, Status.APPROVED)

    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="claims")
    claimant = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="claims")
    message = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # A student can only have one live claim per item.
            models.UniqueConstraint(
                fields=["item", "claimant"],
                condition=Q(status__in=["pending", "approved"]),
                name="claim_one_active_per_student_item",
            ),
            # An item can only ever be handed to one claimant.
            models.UniqueConstraint(
                fields=["item"],
                condition=Q(status="approved"),
                name="claim_one_approved_per_item",
            ),
        ]

    def clean(self):
        # Business rules live on the model so forms, admin and the API all obey them.
        if self._state.adding and self.item_id and self.claimant_id:
            if self.item.created_by_id == self.claimant_id:
                raise ValidationError({"claimant": "You cannot claim an item you posted."})
            if self.item.is_returned:
                raise ValidationError({"item": "This item has already been returned."})

    def __str__(self):
        return f"Claim for {self.item.title} by {self.claimant}"
