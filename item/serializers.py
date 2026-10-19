from django.conf import settings
from rest_framework import serializers

from .models import Item


class ItemSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)

    class Meta:
        model = Item
        fields = [
            "id",
            "title",
            "description",
            "location",
            "status",
            "category",
            "category_name",
            "image",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
            "returned_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at", "returned_at"]

    def validate_image(self, image):
        if image is None:
            return image
        limit = settings.IMAGE_MAX_UPLOAD_BYTES
        if image.size > limit:
            raise serializers.ValidationError(f"Image is too large (max {limit // (1024 * 1024)} MB).")
        # DRF/Pillow already proved it is a real image; only allow common photo formats.
        fmt = getattr(getattr(image, "image", None), "format", None)
        if fmt not in ("JPEG", "PNG", "WEBP"):
            raise serializers.ValidationError("Use a JPEG, PNG or WebP image.")
        return image

    def validate_title(self, title):
        title = title.strip()
        if len(title) < 3:
            raise serializers.ValidationError("Title must be at least 3 characters.")
        return title

    def validate_status(self, status):
        # Returning an item has side effects on claims, so it only happens via /mark-returned/.
        if status == Item.Status.RETURNED:
            raise serializers.ValidationError("Use the mark-returned action to close an item.")
        return status
