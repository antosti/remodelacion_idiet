from django.urls import path
from . import views

urlpatterns = [
    path('list-active-foods/', views.list_active_foods, name='list_active_foods'),
    path('list-deactive-foods/', views.list_deactive_foods, name='list_deactive_foods'),
    path('create-food/', views.create_food, name='create_food'),
]