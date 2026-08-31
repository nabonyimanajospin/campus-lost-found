"""
URL configuration for campus_lost_found project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('student.urls')),
    path('items/', include('item.urls')),
    path('claims/', include('claim.urls')),
    path('categories/', include('category.urls')),
]
