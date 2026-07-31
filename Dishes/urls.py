from django.urls import path
from . import views

urlpatterns = [
    path('create-dish/', views.create_dish, name='create_dish'),
    path('list-active-dishes/', views.list_active_dishes, name='list_active_dishes'),
    path('list-deactive-dishes/', views.list_deactive_dishes, name='list_deactive_dishes'),
    path('dishes/<int:id>/edit/', views.edit_dish, name='edit_dish'),
    path('dishes/<int:id>/deactivate/', views.deactivate_dish, name='deactivate_dish'),
    path('dishes/<int:id>/reactivate/', views.reactivate_dish, name='reactivate_dish'),
    path('dishes/<int:id>/delete/', views.delete_dish, name='delete_dish'),
]