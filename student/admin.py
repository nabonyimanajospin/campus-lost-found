from django.contrib import admin

from .models import Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("full_name", "email", "phone", "user", "created_at")
    search_fields = ("first_name", "last_name", "email", "phone")
    raw_id_fields = ("user",)
