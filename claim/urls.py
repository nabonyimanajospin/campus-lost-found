from django.urls import path
from . import views

urlpatterns = [
    path('', views.claim_list, name='claim_list'),
    path('add/', views.claim_create, name='claim_create'),
]
