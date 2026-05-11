from django.urls import path
from . import views

urlpatterns = [
    path('create-dish/', views.create_dish, name='create_dish'),
]