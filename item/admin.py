from django.contrib import admin

from .models import Item


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "category", "created_by", "created_at")
    list_filter = ("status", "category")
    search_fields = ("title", "description", "location")
    raw_id_fields = ("created_by",)
    readonly_fields = ("created_at", "updated_at", "returned_at")
