from django.urls import path
from . import views

urlpatterns = [
    path('clients/<int:id>/create-diet/', views.create_diet, name='create_diet'),
    path('clients/<int:id>/diets/', views.client_diets, name='client_diets'),
    path('clients/<int:client_id>/diets/<int:menu_id>/', views.diet_detail, name='diet_detail'),
]
