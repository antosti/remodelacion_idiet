from django.urls import path
from . import views

urlpatterns = [
    path('create-dish/', views.create_dish, name='create_dish'),
    path('list-active-dishes/', views.list_active_dishes, name='list_active_dishes'),
    path('list-deactive-dishes/', views.list_deactive_dishes, name='list_deactive_dishes'),
]