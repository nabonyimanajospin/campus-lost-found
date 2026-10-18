"""Versioned REST API, mounted at /api/v1/."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from category.api_views import CategoryViewSet
from claim.api_views import ClaimViewSet
from item.api_views import ItemViewSet
from student.api_views import LoginView, LogoutView, MeView, RegisterView, StudentViewSet

router = DefaultRouter()
router.register("items", ItemViewSet, basename="item")
router.register("claims", ClaimViewSet, basename="claim")
router.register("categories", CategoryViewSet, basename="category")
router.register("students", StudentViewSet, basename="student")

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="api_register"),
    path("auth/login/", LoginView.as_view(), name="api_login"),
    path("auth/logout/", LogoutView.as_view(), name="api_logout"),
    path("auth/me/", MeView.as_view(), name="api_me"),
    path("", include(router.urls)),
]
