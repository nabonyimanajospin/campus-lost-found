from django.urls import path
from . import views

urlpatterns = [
    path('', views.category_list, name='category_list'),
    path('add/', views.category_create, name='category_create'),
]
