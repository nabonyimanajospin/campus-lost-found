import uuid
from pathlib import Path

from django.db import models
from django.utils import timezone

from category.models import Category
from student.models import Student


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def item_image_path(instance, filename):
    # Random name: no user-controlled filenames on disk and no guessable URLs.
    # Only known image extensions survive, so an upload can never be served as HTML/JS.
    ext = Path(filename).suffix.lower()
    if ext not in IMAGE_EXTENSIONS:
        ext = ".jpg"
    return f"items/{uuid.uuid4().hex}{ext}"


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
    image = models.ImageField(upload_to=item_image_path, null=True, blank=True)
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
