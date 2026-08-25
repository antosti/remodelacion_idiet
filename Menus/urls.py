from django.urls import path
from . import views

urlpatterns = [
    path('clients/<int:id>/create-diet/', views.create_diet, name='create_diet'),
    path('clients/<int:id>/diets/', views.client_diets, name='client_diets'),
    path('clients/<int:client_id>/diets/<int:menu_id>/', views.diet_detail, name='diet_detail'),
    path('clients/<int:client_id>/diets/<int:menu_id>/intake/<int:item_id>/edit/',
         views.edit_menu_intake, name='edit_menu_intake'),
    path('clients/<int:client_id>/diets/<int:menu_id>/regenerate/',
         views.regenerate_menu, name='regenerate_menu'),
    path('clients/<int:client_id>/diets/<int:menu_id>/delete/',
         views.delete_menu, name='delete_menu'),
]
