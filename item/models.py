from django.db import models
from django.utils import timezone

from category.models import Category
from student.models import Student


class Item(models.Model):
    class Status(models.TextChoices):
        LOST = "lost", "Lost"
        FOUND = "found", "Found"
        RETURNED = "returned", "Returned"

    title = models.CharField(max_length=200)
    description = models.TextField()
    location = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.LOST)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="items",
    )
    created_by = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="items")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    returned_at = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
        ]

    def save(self, *args, **kwargs):
        # Keep returned_at consistent with status no matter how the item is saved.
        if self.status == self.Status.RETURNED and self.returned_at is None:
            self.returned_at = timezone.now()
        elif self.status != self.Status.RETURNED:
            self.returned_at = None
        super().save(*args, **kwargs)

    @property
    def is_returned(self):
        return self.status == self.Status.RETURNED

    def __str__(self):
        return self.title
