"""
URL configuration for campus_lost_found project.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('campus_lost_found.api')),
    path('', include('student.urls')),
    path('items/', include('item.urls')),
    path('claims/', include('claim.urls')),
    path('categories/', include('category.urls')),
    path('app/', include('frontend.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
