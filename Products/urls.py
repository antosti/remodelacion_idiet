from django.urls import path
from . import views

urlpatterns = [
    path('list-active-foods/', views.list_active_foods, name='list_active_foods'),
    path('list-deactive-foods/', views.list_deactive_foods, name='list_deactive_foods'),
    path('foods/<int:id>/deactivate/', views.deactivate_food, name='deactivate_food'),
    path('foods/deactivate-bulk/', views.deactivate_foods_bulk, name='deactivate_foods_bulk'),
    path('foods/<int:id>/reactivate/', views.reactivate_food, name='reactivate_food'),
    path('foods/reactivate-bulk/', views.reactivate_foods_bulk, name='reactivate_foods_bulk'),
    path('foods/<int:id>/delete/', views.delete_food, name='delete_food'),
    path('foods/delete-bulk/', views.delete_foods_bulk, name='delete_foods_bulk'),
    path('create-food/', views.create_food, name='create_food'),
]
