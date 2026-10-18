from django.contrib import admin

from .models import Claim


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ("item", "claimant", "status", "created_at")
    list_filter = ("status",)
    raw_id_fields = ("item", "claimant")
    # Status changes must go through claim.services (approve/reject/withdraw) via the API.
    readonly_fields = ("status", "created_at", "updated_at", "resolved_at")
